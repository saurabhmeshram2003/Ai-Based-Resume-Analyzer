"""
Comprehensive skills dictionary with 200+ skills organized by category.
Used by the scoring engine to identify matched/missing skills.
"""

SKILLS_BY_CATEGORY = {
    "programming": [
        "python", "java", "javascript", "typescript", "c++", "c#", "go", "golang",
        "rust", "swift", "kotlin", "ruby", "php", "scala", "r", "matlab", "perl",
        "bash", "shell scripting", "powershell", "vba", "dart", "lua", "haskell",
        "elixir", "erlang", "cobol", "fortran", "assembly", "groovy", "objective-c",
        "solidity", "julia", "crystal", "nim", "zig"
    ],
    "frameworks": [
        "react", "angular", "vue", "nextjs", "nuxt", "svelte", "gatsby", "astro",
        "django", "flask", "fastapi", "spring boot", "express", "nestjs", "koa",
        "laravel", "rails", "asp.net", "hibernate", "graphql", "grpc",
        "react native", "flutter", "ionic", "electron", "tauri",
        "tailwind", "bootstrap", "material ui", "chakra ui", "ant design",
        "redux", "zustand", "mobx", "rxjs", "jquery", "alpinejs",
        "pytorch lightning", "hugging face transformers", "langchain", "llamaindex"
    ],
    "databases": [
        "mysql", "postgresql", "mongodb", "sqlite", "redis", "elasticsearch",
        "cassandra", "dynamodb", "oracle", "mssql", "sql server", "mariadb", "couchdb",
        "neo4j", "firebase", "supabase", "cockroachdb", "clickhouse", "snowflake",
        "bigquery", "redshift", "databricks", "pinecone", "weaviate", "chroma",
        "influxdb", "timescaledb", "citus"
    ],
    "cloud_devops": [
        "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s",
        "jenkins", "terraform", "ansible", "github actions", "gitlab ci",
        "circleci", "travis ci", "nginx", "apache", "linux", "unix", "ci/cd",
        "devops", "sre", "cloudformation", "helm", "istio", "prometheus",
        "grafana", "datadog", "new relic", "splunk", "elk stack", "airflow",
        "kafka", "spark", "hadoop", "microservices", "serverless", "lambda",
        "ec2", "s3", "rds", "vpc", "cloudwatch", "cloudfront", "route53",
        "azure devops", "aks", "eks", "gke", "cloud run", "cloud functions",
        "pulumi", "vagrant", "packer", "consul", "vault", "linkerd"
    ],
    "data_ml": [
        "tensorflow", "pytorch", "scikit-learn", "keras", "pandas", "numpy",
        "matplotlib", "seaborn", "plotly", "tableau", "power bi", "excel",
        "sql", "nosql", "data analysis", "machine learning", "deep learning",
        "natural language processing", "nlp", "computer vision", "mlops",
        "feature engineering", "data pipelines", "etl", "data engineering",
        "statistics", "a/b testing", "data visualization", "xgboost", "lightgbm",
        "catboost", "random forest", "gradient boosting", "svm", "neural networks",
        "transformers", "bert", "gpt", "llm", "openai", "generative ai", "rag",
        "vector database", "opencv", "nltk", "spacy", "pdfplumber",
        "dbt", "fivetran", "great expectations", "mlflow", "weights & biases",
        "kubeflow", "sagemaker", "vertex ai", "azure ml", "data bricks",
        "time series", "forecasting", "anomaly detection", "recommendation systems"
    ],
    "soft_skills": [
        "leadership", "communication", "problem solving", "teamwork", "collaboration",
        "project management", "agile", "scrum", "kanban", "jira", "confluence",
        "time management", "critical thinking", "adaptability", "creativity",
        "mentoring", "stakeholder management", "presentations", "negotiation",
        "conflict resolution", "decision making", "strategic thinking",
        "customer focus", "attention to detail", "analytical thinking",
        "cross-functional collaboration", "product thinking", "growth mindset"
    ],
    "business_tools": [
        "salesforce", "sap", "hubspot", "zendesk", "slack", "notion", "asana",
        "figma", "sketch", "adobe xd", "photoshop", "illustrator", "invision",
        "google analytics", "mixpanel", "amplitude", "segment", "looker",
        "product management", "business analysis", "crm", "erp",
        "microsoft office", "google workspace", "excel", "powerpoint",
        "monday.com", "linear", "trello", "miro", "lucidchart"
    ],
    "testing": [
        "selenium", "playwright", "cypress", "jest", "pytest", "junit",
        "mocha", "chai", "jasmine", "testng", "postman", "swagger",
        "unit testing", "integration testing", "e2e testing", "tdd", "bdd",
        "load testing", "performance testing", "api testing", "jmeter",
        "locust", "k6", "gatling", "cucumber", "behave", "robot framework",
        "appium", "detox", "xctestframework", "espresso"
    ],
    "security": [
        "cybersecurity", "penetration testing", "owasp", "ssl/tls",
        "oauth", "jwt", "encryption", "network security", "firewalls",
        "soc", "siem", "vulnerability assessment", "ethical hacking",
        "zero trust", "iam", "pki", "sast", "dast", "devsecops",
        "burp suite", "nmap", "metasploit", "wireshark", "snort"
    ],
    "mobile": [
        "android", "ios", "react native", "flutter", "swift", "kotlin",
        "xcode", "android studio", "mobile development", "pwa",
        "expo", "capacitor", "cordova", "mobile ui", "ux design",
        "app store optimization", "push notifications", "deep linking"
    ],
    "api_architecture": [
        "rest api", "restful", "graphql", "grpc", "websockets", "webhooks",
        "api design", "api gateway", "microservices", "event-driven",
        "message queuing", "rabbitmq", "kafka", "nats", "pub/sub",
        "system design", "distributed systems", "high availability",
        "load balancing", "caching", "cdn", "api versioning",
        "openapi", "swagger", "postman", "insomnia"
    ]
}

# Flat list for fast lookup
SKILLS_FLAT = list(set(
    skill for category_skills in SKILLS_BY_CATEGORY.values()
    for skill in category_skills
))

# Sorted by length descending for greedy matching (longer phrases first)
SKILLS_FLAT_SORTED = sorted(SKILLS_FLAT, key=len, reverse=True)
