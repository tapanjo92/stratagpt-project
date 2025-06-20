import json
import boto3
import os
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime
import time
from dataclasses import dataclass
import statistics

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
lambda_client = boto3.client('lambda')
bedrock = boto3.client('bedrock-runtime')

@dataclass
class TestQuestion:
    question: str
    expected_topics: List[str]
    category: str
    difficulty: str  # easy, medium, hard

@dataclass
class EvaluationResult:
    question: str
    answer: str
    accuracy_score: float
    response_time_ms: int
    citations_count: int
    topics_covered: List[str]
    passed: bool

class StrataEvaluationHarness:
    def __init__(self):
        self.rag_lambda_name = os.environ.get('RAG_LAMBDA_NAME', '')
        self.bedrock_model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-opus-20240229-v1:0')
        
        # Define test questions for Australian strata context
        self.test_questions = [
            # Easy questions
            TestQuestion(
                question="What is the quorum required for an Annual General Meeting?",
                expected_topics=["quorum", "AGM", "annual general meeting", "attendance"],
                category="meetings",
                difficulty="easy"
            ),
            TestQuestion(
                question="How much notice must be given for an AGM?",
                expected_topics=["notice period", "AGM", "days", "notification"],
                category="meetings",
                difficulty="easy"
            ),
            TestQuestion(
                question="Can pets be kept in a strata property?",
                expected_topics=["pets", "by-laws", "animals", "approval"],
                category="by-laws",
                difficulty="easy"
            ),
            
            # Medium questions
            TestQuestion(
                question="What are the requirements for passing a special resolution?",
                expected_topics=["special resolution", "75%", "voting", "majority"],
                category="governance",
                difficulty="medium"
            ),
            TestQuestion(
                question="How are strata levies calculated and when are they due?",
                expected_topics=["levies", "calculation", "unit entitlement", "due date"],
                category="finance",
                difficulty="medium"
            ),
            TestQuestion(
                question="What maintenance is the owners corporation responsible for?",
                expected_topics=["common property", "maintenance", "repairs", "responsibility"],
                category="maintenance",
                difficulty="medium"
            ),
            TestQuestion(
                question="What is the process for amending by-laws?",
                expected_topics=["by-laws", "amendment", "special resolution", "registration"],
                category="by-laws",
                difficulty="medium"
            ),
            
            # Hard questions
            TestQuestion(
                question="What are the legal requirements for capital works fund contributions?",
                expected_topics=["capital works fund", "10-year plan", "contributions", "legislation"],
                category="finance",
                difficulty="hard"
            ),
            TestQuestion(
                question="How does the strata committee deal with breaches of by-laws?",
                expected_topics=["breach", "notice", "tribunal", "enforcement", "penalties"],
                category="compliance",
                difficulty="hard"
            ),
            TestQuestion(
                question="What are the disclosure requirements when selling a strata unit?",
                expected_topics=["disclosure", "section 184", "certificate", "selling"],
                category="transactions",
                difficulty="hard"
            ),
            
            # State-specific questions
            TestQuestion(
                question="What are the key differences between NSW and QLD strata legislation?",
                expected_topics=["NSW", "Queensland", "legislation", "differences"],
                category="legislation",
                difficulty="hard"
            ),
            TestQuestion(
                question="What is the role of Fair Trading in strata disputes?",
                expected_topics=["Fair Trading", "disputes", "mediation", "tribunal"],
                category="disputes",
                difficulty="medium"
            ),
            
            # Practical scenarios
            TestQuestion(
                question="A lot owner wants to renovate their bathroom. What approvals are needed?",
                expected_topics=["renovation", "approval", "by-laws", "common property"],
                category="renovations",
                difficulty="medium"
            ),
            TestQuestion(
                question="How can the strata committee terminate a strata manager's contract?",
                expected_topics=["termination", "contract", "strata manager", "notice"],
                category="management",
                difficulty="hard"
            ),
            TestQuestion(
                question="What insurance must an owners corporation have?",
                expected_topics=["insurance", "building", "public liability", "workers compensation"],
                category="insurance",
                difficulty="medium"
            ),
            
            # Financial questions
            TestQuestion(
                question="How are unpaid levies recovered from lot owners?",
                expected_topics=["unpaid levies", "recovery", "interest", "legal action"],
                category="finance",
                difficulty="medium"
            ),
            TestQuestion(
                question="What financial records must the owners corporation keep?",
                expected_topics=["financial records", "books", "audit", "retention"],
                category="finance",
                difficulty="medium"
            ),
            
            # Emergency situations
            TestQuestion(
                question="Who is responsible for emergency repairs in common property?",
                expected_topics=["emergency", "repairs", "common property", "reimbursement"],
                category="maintenance",
                difficulty="medium"
            ),
            TestQuestion(
                question="What constitutes a valid proxy for strata meetings?",
                expected_topics=["proxy", "form", "validity", "limitations"],
                category="meetings",
                difficulty="easy"
            ),
            TestQuestion(
                question="Can the strata committee make decisions via email?",
                expected_topics=["email", "decisions", "circular resolution", "voting"],
                category="governance",
                difficulty="medium"
            )
        ]
    
    def invoke_rag_query(self, question: str, tenant_id: str = "test-tenant") -> Tuple[Dict[str, Any], int]:
        """Invoke the RAG Lambda function"""
        start_time = time.time()
        
        try:
            response = lambda_client.invoke(
                FunctionName=self.rag_lambda_name,
                InvocationType='RequestResponse',
                Payload=json.dumps({
                    'question': question,
                    'tenant_id': tenant_id,
                    'max_results': 10,
                    'include_citations': True,
                    'answer_style': 'professional'
                })
            )
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Parse response
            payload = json.loads(response['Payload'].read())
            body = json.loads(payload.get('body', '{}')) if isinstance(payload.get('body'), str) else payload
            
            return body, response_time_ms
            
        except Exception as e:
            logger.error(f"Error invoking RAG Lambda: {str(e)}")
            return {'error': str(e)}, int((time.time() - start_time) * 1000)
    
    def evaluate_answer_accuracy(self, answer: str, expected_topics: List[str], 
                               question: str) -> Tuple[float, List[str]]:
        """Evaluate answer accuracy using Bedrock"""
        try:
            evaluation_prompt = f"""Evaluate the following answer to a strata management question.

QUESTION: {question}

ANSWER: {answer}

EXPECTED TOPICS TO COVER: {', '.join(expected_topics)}

Please evaluate:
1. Does the answer address the question accurately? (0-10 score)
2. Which expected topics were covered? (list them)
3. Is the answer factually correct for Australian strata law? (0-10 score)
4. Is the answer practical and actionable? (0-10 score)

Provide your evaluation in the following JSON format:
{{
    "relevance_score": 0-10,
    "topics_covered": ["topic1", "topic2"],
    "accuracy_score": 0-10,
    "practicality_score": 0-10,
    "overall_score": 0-10,
    "feedback": "brief explanation"
}}"""

            request_body = {
                "messages": [
                    {
                        "role": "user",
                        "content": evaluation_prompt
                    }
                ],
                "max_tokens": 500,
                "temperature": 0.1,
                "anthropic_version": "bedrock-2023-05-31"
            }
            
            response = bedrock.invoke_model(
                modelId=self.bedrock_model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            evaluation_text = response_body.get('content', [{}])[0].get('text', '{}')
            
            # Parse JSON from response
            import re
            json_match = re.search(r'\{[^}]+\}', evaluation_text, re.DOTALL)
            if json_match:
                evaluation = json.loads(json_match.group())
                overall_score = evaluation.get('overall_score', 5) / 10.0
                topics_covered = evaluation.get('topics_covered', [])
                return overall_score, topics_covered
            
            return 0.5, []
            
        except Exception as e:
            logger.error(f"Error evaluating answer: {str(e)}")
            # Fallback to simple keyword matching
            topics_covered = [topic for topic in expected_topics 
                            if topic.lower() in answer.lower()]
            score = len(topics_covered) / len(expected_topics) if expected_topics else 0.5
            return score, topics_covered
    
    def run_single_test(self, test_question: TestQuestion) -> EvaluationResult:
        """Run a single test question"""
        logger.info(f"Testing: {test_question.question}")
        
        # Invoke RAG
        response, response_time = self.invoke_rag_query(test_question.question)
        
        if 'error' in response:
            return EvaluationResult(
                question=test_question.question,
                answer=f"Error: {response['error']}",
                accuracy_score=0.0,
                response_time_ms=response_time,
                citations_count=0,
                topics_covered=[],
                passed=False
            )
        
        answer = response.get('answer', '')
        citations = response.get('citations', [])
        
        # Evaluate accuracy
        accuracy_score, topics_covered = self.evaluate_answer_accuracy(
            answer, test_question.expected_topics, test_question.question
        )
        
        # Determine if test passed (>= 90% accuracy)
        passed = accuracy_score >= 0.9 and response_time < 3000
        
        return EvaluationResult(
            question=test_question.question,
            answer=answer[:500] + '...' if len(answer) > 500 else answer,
            accuracy_score=accuracy_score,
            response_time_ms=response_time,
            citations_count=len(citations),
            topics_covered=topics_covered,
            passed=passed
        )
    
    def run_evaluation_suite(self) -> Dict[str, Any]:
        """Run the full evaluation suite"""
        start_time = datetime.utcnow()
        results = []
        
        for test_question in self.test_questions:
            result = self.run_single_test(test_question)
            results.append(result)
            
            # Log individual result
            logger.info(f"Result - Question: {test_question.question[:50]}... "
                       f"Score: {result.accuracy_score:.2f}, "
                       f"Time: {result.response_time_ms}ms, "
                       f"Passed: {result.passed}")
        
        # Calculate summary statistics
        accuracy_scores = [r.accuracy_score for r in results]
        response_times = [r.response_time_ms for r in results]
        passed_count = sum(1 for r in results if r.passed)
        
        summary = {
            'total_questions': len(self.test_questions),
            'passed': passed_count,
            'failed': len(self.test_questions) - passed_count,
            'pass_rate': passed_count / len(self.test_questions) * 100,
            'avg_accuracy': statistics.mean(accuracy_scores),
            'min_accuracy': min(accuracy_scores),
            'max_accuracy': max(accuracy_scores),
            'avg_response_time_ms': statistics.mean(response_times),
            'p95_response_time_ms': sorted(response_times)[int(len(response_times) * 0.95)],
            'max_response_time_ms': max(response_times),
            'evaluation_time_seconds': (datetime.utcnow() - start_time).total_seconds()
        }
        
        # Group results by category
        by_category = {}
        for i, result in enumerate(results):
            category = self.test_questions[i].category
            if category not in by_category:
                by_category[category] = []
            by_category[category].append({
                'question': result.question,
                'score': result.accuracy_score,
                'time_ms': result.response_time_ms,
                'passed': result.passed
            })
        
        return {
            'summary': summary,
            'detailed_results': [
                {
                    'question': r.question,
                    'answer_preview': r.answer[:200] + '...' if len(r.answer) > 200 else r.answer,
                    'accuracy_score': r.accuracy_score,
                    'response_time_ms': r.response_time_ms,
                    'citations_count': r.citations_count,
                    'topics_covered': r.topics_covered,
                    'passed': r.passed
                }
                for r in results
            ],
            'by_category': by_category,
            'timestamp': datetime.utcnow().isoformat()
        }

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler"""
    logger.info("Starting RAG evaluation suite")
    
    harness = StrataEvaluationHarness()
    results = harness.run_evaluation_suite()
    
    # Log summary
    summary = results['summary']
    logger.info(f"Evaluation complete - Pass rate: {summary['pass_rate']:.1f}%, "
               f"Avg accuracy: {summary['avg_accuracy']:.2f}, "
               f"Avg response time: {summary['avg_response_time_ms']:.0f}ms")
    
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }