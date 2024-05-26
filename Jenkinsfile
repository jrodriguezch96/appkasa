pipeline {
    agent { label 'docker-node' }
    
    
    environment {
        DOCKER_REGISTRY = 'appkasa'
        DOCKER_IMAGE = 'node-10'
        DOCKER_TAG = "${env.BRANCH_NAME}"
    }

    stages {


        stage('Configuration environments') {
            steps {
                script {
                    echo 'Configuration environments...' + env.BRANCH_NAME
					try {
						echo 'en try'
					} catch (Exception e) {
						currentBuild.result = 'FAILURE'
						error "Error durante la configuración de entornos: ${e.message}"
					}
                }
            }
        }


        stage('Building Angular App') {
            steps {
                script {
                    echo 'Building Angular App...' + env.BRANCH_NAME
                }
            }
        }

        stage('Deploying Code') {
            steps {
                script {
                    echo 'Deploying...' + env.BRANCH_NAME

                    // Obtener el ID del contenedor en ejecución actualmente
                    def currentContainerId = sh(script: "docker ps -q --filter ancestor=appkasa-web", returnStdout: true).trim()

                    if (currentContainerId) {
						sh "docker stop ${currentContainerId}"
					} else {
						echo "No se encontró ningún contenedor para detener."
					}
                    sh "docker-compose up --build"
                    
                }
            }
        }
    }
}
