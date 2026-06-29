# TapInShift AWS Deployment

This directory contains the AWS serverless baseline for cloud queue sync.

## Resources

- Lambda Function URL
- DynamoDB table `TapInShiftEvents`
- GSI `GSI1` for `SYNC#queued` and `SYNC#claimed`
- Lambda execution role with DynamoDB read/write/query access

## Deploy Outline

1. Build a Lambda zip that contains `tapinshift` and runtime dependencies.
2. Deploy `infra/aws/cloudformation.yaml`.
3. Update the Lambda code artifact.
4. Set Slack Request URLs to the Function URL:
   - Events: `<FunctionUrl>/slack/events`
   - Interactivity: `<FunctionUrl>/slack/actions`
5. Set Windows `.env.local`:
   - `TAPINSHIFT_CLOUD_ENDPOINT=<FunctionUrl>`
   - `TAPINSHIFT_SYNC_TOKEN=<same token as CloudFormation parameter>`

The template intentionally uses `AuthType: NONE` for the Function URL because Slack cannot send AWS IAM signatures. Slack requests are protected by Slack signing secret verification, and Windows sync requests are protected by the bearer token.
