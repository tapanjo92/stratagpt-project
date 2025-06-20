import * as cdk from 'aws-cdk-lib';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as cloudwatch_actions from 'aws-cdk-lib/aws-cloudwatch-actions';
import { Construct } from 'constructs';

export class MonitoringStack extends cdk.Stack {
  public readonly alarmTopic: sns.Topic;
  public readonly dashboard: cloudwatch.Dashboard;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);
    
    // SNS Topic for alarms
    this.alarmTopic = new sns.Topic(this, 'AlarmTopic', {
      topicName: 'strata-alarms',
      displayName: 'Strata GPT Alarms'
    });

    // CloudWatch Dashboard
    this.dashboard = new cloudwatch.Dashboard(this, 'IngestionDashboard', {
      dashboardName: 'strata-ingestion-pipeline',
      defaultInterval: cdk.Duration.hours(1)
    });

    // Log Groups for Lambda functions
    const logGroups = {
      textract: new logs.LogGroup(this, 'TextractLogGroup', {
        logGroupName: '/aws/lambda/textract-processor',
        retention: logs.RetentionDays.ONE_YEAR,
        removalPolicy: cdk.RemovalPolicy.DESTROY
      }),
      chunker: new logs.LogGroup(this, 'ChunkerLogGroup', {
        logGroupName: '/aws/lambda/chunk-sanitizer',
        retention: logs.RetentionDays.ONE_YEAR,
        removalPolicy: cdk.RemovalPolicy.DESTROY
      }),
      embeddings: new logs.LogGroup(this, 'EmbeddingsLogGroup', {
        logGroupName: '/aws/lambda/embeddings-generator',
        retention: logs.RetentionDays.ONE_YEAR,
        removalPolicy: cdk.RemovalPolicy.DESTROY
      })
    };

    // Metric filters for errors
    const errorMetricFilter = new logs.MetricFilter(this, 'ErrorMetricFilter', {
      logGroup: logGroups.textract,
      metricNamespace: 'StrataGPT/Ingestion',
      metricName: 'Errors',
      filterPattern: logs.FilterPattern.literal('[ERROR]'),
      metricValue: '1'
    });

    // Custom metrics
    const metrics = {
      documentsProcessed: new cloudwatch.Metric({
        namespace: 'StrataGPT/Ingestion',
        metricName: 'DocumentsProcessed',
        statistic: 'Sum'
      }),
      processingDuration: new cloudwatch.Metric({
        namespace: 'StrataGPT/Ingestion',
        metricName: 'ProcessingDuration',
        statistic: 'Average',
        unit: cloudwatch.Unit.MILLISECONDS
      }),
      embeddingLatency: new cloudwatch.Metric({
        namespace: 'StrataGPT/Ingestion',
        metricName: 'EmbeddingLatency',
        statistic: 'Average',
        unit: cloudwatch.Unit.MILLISECONDS
      }),
      chunkCount: new cloudwatch.Metric({
        namespace: 'StrataGPT/Ingestion',
        metricName: 'ChunksGenerated',
        statistic: 'Sum'
      })
    };

    // Alarms
    const errorAlarm = new cloudwatch.Alarm(this, 'ErrorAlarm', {
      metric: errorMetricFilter.metric(),
      threshold: 5,
      evaluationPeriods: 1,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      alarmDescription: 'Too many errors in ingestion pipeline'
    });

    const processingTimeAlarm = new cloudwatch.Alarm(this, 'ProcessingTimeAlarm', {
      metric: metrics.processingDuration,
      threshold: 300000, // 5 minutes
      evaluationPeriods: 2,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      alarmDescription: 'Document processing taking too long'
    });

    // Add alarm actions
    errorAlarm.addAlarmAction(new cloudwatch_actions.SnsAction(this.alarmTopic));
    processingTimeAlarm.addAlarmAction(new cloudwatch_actions.SnsAction(this.alarmTopic));

    // Dashboard widgets
    this.dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Documents Processed',
        left: [metrics.documentsProcessed],
        width: 12
      }),
      new cloudwatch.GraphWidget({
        title: 'Processing Duration',
        left: [metrics.processingDuration],
        width: 12
      })
    );

    this.dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Embedding Latency',
        left: [metrics.embeddingLatency],
        width: 12
      }),
      new cloudwatch.GraphWidget({
        title: 'Chunks Generated',
        left: [metrics.chunkCount],
        width: 12
      })
    );

    this.dashboard.addWidgets(
      new cloudwatch.SingleValueWidget({
        title: 'Total Documents Today',
        metrics: [metrics.documentsProcessed],
        period: cdk.Duration.days(1),
        width: 6
      }),
      new cloudwatch.SingleValueWidget({
        title: 'Average Processing Time',
        metrics: [metrics.processingDuration],
        period: cdk.Duration.hours(1),
        width: 6
      }),
      new cloudwatch.SingleValueWidget({
        title: 'Error Count',
        metrics: [errorMetricFilter.metric()],
        period: cdk.Duration.hours(1),
        width: 6
      })
    );

    // Log Insights queries
    const queries = [
      {
        name: 'Recent Errors',
        query: `fields @timestamp, @message
          | filter @message like /ERROR/
          | sort @timestamp desc
          | limit 20`
      },
      {
        name: 'Processing Performance',
        query: `fields @timestamp, @duration
          | filter @type = "REPORT"
          | stats avg(@duration), max(@duration), min(@duration) by bin(5m)`
      }
    ];

    // Outputs
    new cdk.CfnOutput(this, 'DashboardURL', {
      value: `https://console.aws.amazon.com/cloudwatch/home?region=${this.region}#dashboards:name=${this.dashboard.dashboardName}`,
      description: 'CloudWatch Dashboard URL'
    });

    new cdk.CfnOutput(this, 'AlarmTopicArn', {
      value: this.alarmTopic.topicArn,
      exportName: `${this.stackName}-AlarmTopicArn`
    });
  }
}