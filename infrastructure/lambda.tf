resource "aws_lambda_function" "fastapi" {
  function_name    = "${local.app_name}-fastapi"
  role             = aws_iam_role.lambda_role.arn
  runtime          = "python3.14"
  handler          = "app.api_handler.handler"

  s3_bucket        = var.artifacts_bucket
  s3_key           = "${var.app_name}/api-${var.lambda_hash}.zip"

  source_code_hash = base64encode(var.lambda_hash)

  timeout     = var.timeout
  memory_size = var.memory_size

  layers = [
    aws_lambda_layer_version.requirements_lambda_layer.arn,
    "arn:aws:lambda:${var.aws_region}:017000801446:layer:AWSLambdaPowertoolsPythonV3-python314-${var.architecture}:28"
  ]

  environment {
    variables = {
      APP_NAME                             = var.app_name
      DEBUG                                = var.debug
      DEFAULT_TIMEZONE                     = var.default_timezone
      LOG_LEVEL                            = var.log_level
      POWERTOOLS_LOGGER_LOG_EVENT          = "true"
      POWERTOOLS_SERVICE_NAME              = var.power_tools_service_name
      POWERTOOLS_DEBUG                     = "false"
      STAGE                                = var.stage
      CACHE_SERVICE_API_KEY_SSM_PARAM_NAME = var.cache_service_api_key_ssm_param_name
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_policy_attachment,
    aws_lambda_layer_version.requirements_lambda_layer,
  ]
}
