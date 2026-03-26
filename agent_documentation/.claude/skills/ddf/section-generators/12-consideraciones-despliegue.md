# Generador: Consideraciones de Despliegue

> **Sección 12 de 12** del Documento de Diseño Funcional

---

## Contexto de orientación

Recibes la estructura general del proyecto. DEBES leer los archivos de
infraestructura reales para documentar el despliegue con configuraciones concretas.

---

## Exploración Requerida

### Lecturas obligatorias
- `Dockerfile` si existe (revela imagen base, stages, ports expuestos)
- `docker-compose.yml` o `docker-compose.yaml` si existe (revela servicios y sus configs)
- Al menos 1 archivo de CI/CD (`.github/workflows/*.yml`, `.gitlab-ci.yml`, `Jenkinsfile`)

### Búsquedas dirigidas
- Glob: `Dockerfile*`, `docker-compose*.yml`, `.github/workflows/**`, `k8s/**`, `terraform/**`
- Grep: `ENV |ARG |environment:|EXPOSE` para variables de entorno en contenedores
- Grep: `DATABASE_URL|REDIS_URL|SECRET_KEY` en `.env.example` para dependencias de infra
- Grep: `stage|job:|steps:|pipeline` para estructura de CI/CD

### Lecturas condicionales
- Si existe Kubernetes → leer al menos 2 manifests (deployment.yaml, service.yaml)
- Si existe Terraform o Helm → leer el archivo principal de configuración
- Si existen múltiples docker-compose files → leer todos (revelan diferencias por ambiente)

### Profundidad mínima
- Leer al menos 4 archivos de infraestructura antes de generar
- Documentar el stack completo con versiones reales (imagen Docker, servicios de BD, etc.)

---

## Responsabilidades

1. Identificar ambientes y configuración
2. Documentar estrategia de deployment
3. Describir CI/CD y automatización
4. Listar dependencias e infraestructura

---

## Cobertura Obligatoria

### 1. Ambientes y Configuración (OBLIGATORIO)
**Descripción:** Entornos donde se deploya y cómo se configuran
**Ejemplos:**
- "3 ambientes: desarrollo, staging, producción"
- "Configuración por environment variables (.env files)"
**Qué documentar:**
- Ambientes identificados y cómo se diferencian
- Secrets management
**Dónde buscar en el código:**
- Archivos .env, .env.example
- Config files por ambiente (config.dev, config.prod)
- docker-compose files por ambiente

### 2. Estrategia de Deployment (OBLIGATORIO)
**Descripción:** Cómo se despliega el sistema
**Ejemplos:**
- "Docker containers con docker-compose"
- "Kubernetes manifests para cloud deployment"
- "Serverless con AWS Lambda"
**Qué documentar:**
- Tecnología de deployment (Docker, K8s, VMs, Serverless)
- Proceso de deployment (manual, automatizado)
**Dónde buscar en el código:**
- Dockerfile, docker-compose.yml
- Kubernetes manifests (*.yaml en k8s/)
- Serverless config, Makefile, scripts de deploy

### 3. CI/CD y Automatización (OBLIGATORIO)
**Descripción:** Pipelines de integración y deployment
**Ejemplos:**
- "GitHub Actions pipeline: test → build → deploy"
- "Jenkins con stages: lint, test, security scan, deploy"
**Qué documentar:**
- Herramienta CI/CD usada
- Stages/steps del pipeline
- Triggers (push, PR, manual)
**Dónde buscar en el código:**
- .github/workflows/ (GitHub Actions)
- .gitlab-ci.yml (GitLab CI)
- Jenkinsfile, .circleci/config.yml

### 4. Dependencias e Infraestructura (OBLIGATORIO)
**Descripción:** Servicios y recursos necesarios para operar
**Ejemplos:**
- "Requiere: PostgreSQL 14+, Redis 6+, SMTP server"
- "Cloud: AWS (EC2, RDS, S3, SQS)"
**Qué documentar:**
- Bases de datos (tipo y versión)
- Caches, colas, servicios de mensajería
- Cloud providers y servicios usados
**Dónde buscar en el código:**
- docker-compose.yml (services)
- requirements.txt, package.json (dependencias)
- Infrastructure as Code (Terraform, CloudFormation)
- README con pre-requisitos

---

## Proceso de Generación

### 1. Exploración

```
Glob: Dockerfile*, docker-compose*, .github/workflows/**, .gitlab-ci.yml, k8s/**, deploy/**
Grep: "FROM", "services:", "environment:", "DATABASE_URL", "REDIS_URL"
Read: Dockerfile, docker-compose.yml, archivos de CI/CD, .env.example
```

### 2. Análisis

- Ambientes: de archivos `.env.example`, `docker-compose.override.yml`, configs de CI
- Deployment: de Dockerfile, docker-compose, manifiestos K8s o configs de PaaS
- CI/CD: de `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, etc.
- Dependencias infra: de servicios en docker-compose + `integraciones` en contexto rico

### 3. Sustento

Integrar evidencia de código. Citar Dockerfile, docker-compose y configs de CI al documentar cada aspecto.

**NO** crear bloque separado de "Evidencia analizada" — integrar en hallazgos y desarrollo.

### 4. Validación (Auto-validación)

Antes de entregar verificar:
- [ ] Ambientes identificados y descritos
- [ ] Estrategia de deployment especificada
- [ ] CI/CD documentado (si existe)
- [ ] Dependencias de infraestructura listadas
- [ ] Archivos citados (3 small, 5 medium, 8 large)

---

## Criterios de Completitud

- [ ] Ambientes identificados
- [ ] Estrategia de deployment especificada
- [ ] CI/CD documentado (si existe)
- [ ] Dependencias listadas
- [ ] Archivos citados (3 small, 5 medium, 8 large)


