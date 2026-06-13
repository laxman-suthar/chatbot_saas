pipeline {
    agent any

    environment {
        IMAGE_NAME = 'laxmansuthardev/chatbot-web'
        IMAGE_TAG = "${BUILD_NUMBER}"
        AWS_REGION = 'ap-south-1'
        EKS_CLUSTER = 'chatbot-cluster'
    }

    stages {

        stage('Checkout') {
            steps {
                git branch: 'deployment',
                    url: 'https://github.com/laxman-suthar/chatbot_saas'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh """
                    docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest
                """
            }
        }

        stage('Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-credentials',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                        docker push laxmansuthardev/chatbot-web:${BUILD_NUMBER}
                        docker push laxmansuthardev/chatbot-web:latest
                    '''
                }
            }
        }

        stage('Update kubeconfig') {
            steps {
                withCredentials([aws(
                    credentialsId: 'aws-credentials',
                    accessKeyVariable: 'AWS_ACCESS_KEY_ID',
                    secretKeyVariable: 'AWS_SECRET_ACCESS_KEY'
                )]) {
                    sh """
                        aws eks update-kubeconfig --region ${AWS_REGION} --name ${EKS_CLUSTER}
                    """
                }
            }
        }

        stage('Deploy Secrets to K8s') {
            steps {
                withCredentials([
                    string(credentialsId: 'django-secret-key', variable: 'SECRET_KEY'),
                    string(credentialsId: 'db-password', variable: 'DB_PASSWORD'),
                    string(credentialsId: 'db-user', variable: 'DB_USER'),
                    string(credentialsId: 'db-host', variable: 'DB_HOST'),
                    string(credentialsId: 'google-api-key', variable: 'GOOGLE_API_KEY'),
                    string(credentialsId: 'oauth-key', variable: 'OAUTH_KEY'),
                    aws(
                        credentialsId: 'aws-credentials',
                        accessKeyVariable: 'AWS_ACCESS_KEY_ID',
                        secretKeyVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {
                    sh """
                        kubectl apply -f k8s/00-namespace.yaml

                        kubectl create secret generic chatbot-secrets \
                            --from-literal=SECRET_KEY="${SECRET_KEY}" \
                            --from-literal=DEBUG="False" \
                            --from-literal=ALLOWED_HOSTS="*" \
                            --from-literal=CORS_ALLOW_ALL_ORIGINS="True" \
                            --from-literal=CORS_ORIGINS="http://localhost:3000,http://127.0.0.1" \
                            --from-literal=CSRF_TRUSTED_ORIGINS="http://localhost:3000,http://127.0.0.1" \
                            --from-literal=DB_NAME="postgres" \
                            --from-literal=DB_USER="${DB_USER}" \
                            --from-literal=DB_PASSWORD="${DB_PASSWORD}" \
                            --from-literal=DB_HOST="${DB_HOST}" \
                            --from-literal=DB_PORT="5432" \
                            --from-literal=REDIS_URL="redis://redis-service:6379" \
                            --from-literal=GOOGLE_API_KEY="${GOOGLE_API_KEY}" \
                            --from-literal=GOOGLE_TEXT_MODEL="gemma-3-12b-it" \
                            --from-literal=GOOGLE_EMBEDDING_MODEL="models/gemini-embedding-001" \
                            --from-literal=KAFKA_BOOTSTRAP_SERVERS="kafka-service:9092" \
                            --from-literal=KAFKA_DOCUMENT_UPLOAD_TOPIC="document-upload" \
                            --from-literal=KAFKA_CONSUMER_GROUP="doc-processors" \
                            --from-literal=SOCIAL_AUTH_GOOGLE_OAUTH2_KEY="${OAUTH_KEY}" \
                            --namespace=chatbot \
                            --dry-run=client -o yaml | kubectl apply -f -
                    """
                }
            }
        }

        stage('Deploy to EKS') {
            steps {
                withCredentials([aws(
                    credentialsId: 'aws-credentials',
                    accessKeyVariable: 'AWS_ACCESS_KEY_ID',
                    secretKeyVariable: 'AWS_SECRET_ACCESS_KEY'
                )]) {
                    sh """
                        kubectl apply -f k8s/02-redis.yaml
                        kubectl apply -f k8s/03-kafka.yaml
                        kubectl apply -f k8s/04-kafka-init-job.yaml
                        kubectl apply -f k8s/05-web.yaml
                        kubectl apply -f k8s/06-kafka-consumer.yaml
                        kubectl apply -f k8s/07-nginx.yaml

                        kubectl rollout restart deployment/web -n chatbot
                        kubectl rollout restart deployment/kafka-consumer -n chatbot
                        kubectl rollout status deployment/web -n chatbot --timeout=180s
                    """
                }
            }
        }

        stage('Get App URL') {
            steps {
                withCredentials([aws(
                    credentialsId: 'aws-credentials',
                    accessKeyVariable: 'AWS_ACCESS_KEY_ID',
                    secretKeyVariable: 'AWS_SECRET_ACCESS_KEY'
                )]) {
                    sh """
                        echo "Waiting for LoadBalancer..."
                        sleep 30
                        kubectl get svc nginx-service -n chatbot
                    """
                }
            }
        }
    }

    post {
        success {
            echo '✅ Deployment successful!'
        }
        failure {
            echo '❌ Deployment failed! Check logs above.'
        }
        always {
            sh 'docker logout || true'
        }
    }
}
