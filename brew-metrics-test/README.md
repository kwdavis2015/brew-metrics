# brew-metrics-test

This is a minimal hello-world FastAPI app used exclusively to validate the Docker build pipeline and AWS deployment steps (ECR push, App Runner service, VPC/RDS connectivity).

It is not the production application. Once AWS deployment is validated end-to-end, active development moves to `../brew-metrics/`.
