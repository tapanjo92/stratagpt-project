import json
import boto3
import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
kendra = boto3.client('kendra')
bedrock = boto3.client('bedrock-runtime')
s3 = boto3.client('s3')

@dataclass
class QueryContext:
    question: str
    tenant_id: str
    max_results: int = 10
    include_citations: bool = True
    answer_style: str = "professional"  # professional, simple, detailed

@dataclass
class Citation:
    document_id: str
    document_title: str
    excerpt: str
    page_number: Optional[int]
    confidence_score: float
    s3_uri: Optional[str]

class StrataRAGEngine:
    def __init__(self):
        self.kendra_index_id = os.environ['KENDRA_INDEX_ID']
        self.bedrock_model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-opus-20240229-v1:0')
        self.document_bucket = os.environ['DOCUMENT_BUCKET']
        
    def search_documents(self, context: QueryContext) -> List[Dict[str, Any]]:
        """Search documents using Kendra"""
        try:
            # Build attribute filter for tenant isolation
            attribute_filter = {
                'EqualsTo': {
                    'Key': 'tenant_id',
                    'Value': {
                        'StringValue': context.tenant_id
                    }
                }
            }
            
            # Query Kendra
            response = kendra.query(
                IndexId=self.kendra_index_id,
                QueryText=context.question,
                AttributeFilter=attribute_filter,
                PageSize=context.max_results,
                QueryResultTypeFilter='DOCUMENT'
            )
            
            return response.get('ResultItems', [])
            
        except Exception as e:
            logger.error(f"Kendra search error: {str(e)}")
            return []
    
    def extract_citations(self, search_results: List[Dict[str, Any]]) -> List[Citation]:
        """Extract and format citations from search results"""
        citations = []
        
        for result in search_results:
            try:
                # Extract document attributes
                doc_attributes = result.get('DocumentAttributes', [])
                doc_id = result.get('DocumentId', '')
                
                # Find document title
                title = result.get('DocumentTitle', {}).get('Text', 'Untitled Document')
                
                # Extract excerpt with highlights
                excerpt = result.get('DocumentExcerpt', {}).get('Text', '')
                
                # Get confidence score
                score = result.get('ScoreAttributes', {}).get('ScoreConfidence', 'MEDIUM')
                confidence_map = {'LOW': 0.3, 'MEDIUM': 0.6, 'HIGH': 0.8, 'VERY_HIGH': 0.95}
                confidence = confidence_map.get(score, 0.5)
                
                # Extract S3 URI if available
                s3_uri = None
                for attr in doc_attributes:
                    if attr.get('Key') == '_source_uri':
                        s3_uri = attr.get('Value', {}).get('StringValue')
                
                # Extract page number if available
                page_number = None
                for attr in doc_attributes:
                    if attr.get('Key') == 'page_number':
                        page_number = int(attr.get('Value', {}).get('LongValue', 0))
                
                citations.append(Citation(
                    document_id=doc_id,
                    document_title=title,
                    excerpt=excerpt,
                    page_number=page_number,
                    confidence_score=confidence,
                    s3_uri=s3_uri
                ))
                
            except Exception as e:
                logger.warning(f"Error extracting citation: {str(e)}")
                continue
        
        return citations
    
    def build_strata_prompt(self, context: QueryContext, citations: List[Citation]) -> str:
        """Build a prompt optimized for Australian strata law context"""
        
        # Format citations for the prompt
        citation_text = "\n\n".join([
            f"Document {i+1}: {c.document_title}\n"
            f"Excerpt: {c.excerpt}\n"
            f"Confidence: {c.confidence_score:.0%}"
            for i, c in enumerate(citations[:5])  # Use top 5 citations
        ])
        
        # Style-specific instructions
        style_instructions = {
            "professional": "Provide a professional response suitable for strata managers and committee members.",
            "simple": "Provide a simple, easy-to-understand response for lot owners.",
            "detailed": "Provide a comprehensive response with detailed legal references."
        }
        
        prompt = f"""You are an expert assistant for Australian strata law and management. You help answer questions about strata schemes, by-laws, meeting procedures, and compliance requirements.

IMPORTANT CONTEXT:
- You are answering questions for Australian strata properties
- Cite specific documents and clauses when possible
- Be aware of state-specific legislation (NSW, QLD, VIC, etc.)
- Use Australian spelling and terminology

QUESTION: {context.question}

RELEVANT DOCUMENTS:
{citation_text}

INSTRUCTIONS:
1. {style_instructions.get(context.answer_style, style_instructions['professional'])}
2. Base your answer on the provided documents
3. Include specific citations in [Document N] format
4. If information is unclear or missing, state this explicitly
5. Focus on practical, actionable advice
6. Mention relevant legislation if applicable

RESPONSE:"""
        
        return prompt
    
    def generate_answer(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        """Generate answer using Bedrock"""
        try:
            # Prepare the request
            request_body = {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.3,  # Lower temperature for more factual responses
                "anthropic_version": "bedrock-2023-05-31"
            }
            
            # Invoke Bedrock
            response = bedrock.invoke_model(
                modelId=self.bedrock_model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            answer = response_body.get('content', [{}])[0].get('text', '')
            
            # Extract metrics
            metrics = {
                'input_tokens': response_body.get('usage', {}).get('input_tokens', 0),
                'output_tokens': response_body.get('usage', {}).get('output_tokens', 0),
                'model': self.bedrock_model_id,
                'temperature': 0.3
            }
            
            return answer, metrics
            
        except Exception as e:
            logger.error(f"Bedrock generation error: {str(e)}")
            return "I apologize, but I'm unable to generate a response at this time.", {}
    
    def format_response(self, answer: str, citations: List[Citation]) -> Dict[str, Any]:
        """Format the final response with citations"""
        
        # Extract citation references from the answer
        citation_pattern = r'\[Document (\d+)\]'
        cited_indices = set(int(m.group(1)) - 1 for m in re.finditer(citation_pattern, answer))
        
        # Build citation list
        formatted_citations = []
        for idx in cited_indices:
            if 0 <= idx < len(citations):
                citation = citations[idx]
                formatted_citations.append({
                    'document_id': citation.document_id,
                    'title': citation.document_title,
                    'excerpt': citation.excerpt,
                    'page': citation.page_number,
                    'confidence': citation.confidence_score,
                    's3_uri': citation.s3_uri
                })
        
        return {
            'answer': answer,
            'citations': formatted_citations,
            'total_sources': len(citations),
            'cited_sources': len(formatted_citations)
        }
    
    def process_query(self, context: QueryContext) -> Dict[str, Any]:
        """Main query processing pipeline"""
        start_time = datetime.utcnow()
        
        try:
            # Step 1: Search documents
            logger.info(f"Searching documents for tenant {context.tenant_id}")
            search_results = self.search_documents(context)
            
            if not search_results:
                return {
                    'answer': "I couldn't find any relevant documents to answer your question. Please ensure documents have been uploaded for your strata scheme.",
                    'citations': [],
                    'processing_time_ms': int((datetime.utcnow() - start_time).total_seconds() * 1000)
                }
            
            # Step 2: Extract citations
            citations = self.extract_citations(search_results)
            logger.info(f"Found {len(citations)} relevant documents")
            
            # Step 3: Build prompt
            prompt = self.build_strata_prompt(context, citations)
            
            # Step 4: Generate answer
            answer, metrics = self.generate_answer(prompt)
            
            # Step 5: Format response
            response = self.format_response(answer, citations)
            
            # Add metadata
            response['processing_time_ms'] = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            response['metrics'] = metrics
            response['tenant_id'] = context.tenant_id
            response['timestamp'] = datetime.utcnow().isoformat()
            
            return response
            
        except Exception as e:
            logger.error(f"Query processing error: {str(e)}", exc_info=True)
            return {
                'error': str(e),
                'answer': "I encountered an error processing your query. Please try again.",
                'citations': [],
                'processing_time_ms': int((datetime.utcnow() - start_time).total_seconds() * 1000)
            }

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler"""
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Extract parameters
    body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event
    
    # Create query context
    query_context = QueryContext(
        question=body.get('question', ''),
        tenant_id=body.get('tenant_id', 'default'),
        max_results=body.get('max_results', 10),
        include_citations=body.get('include_citations', True),
        answer_style=body.get('answer_style', 'professional')
    )
    
    # Validate input
    if not query_context.question:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Question is required'})
        }
    
    # Process query
    engine = StrataRAGEngine()
    result = engine.process_query(query_context)
    
    # Return response
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(result)
    }