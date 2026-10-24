import re
from typing import Dict, List, Optional, Set, Tuple

# Canonical mapping of lowercase aliases/variations to authoritative skill name
CANONICAL_SKILL_MAP: Dict[str, str] = {
    # JavaScript / TypeScript / Node
    "javascript": "JavaScript",
    "js": "JavaScript",
    "ecmascript": "JavaScript",
    "es6": "JavaScript",
    "es6+": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "node": "Node.js",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    
    # Frontend Frameworks & Libraries
    "react": "React",
    "react.js": "React",
    "reactjs": "React",
    "react native": "React Native",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "next": "Next.js",
    "vue": "Vue.js",
    "vue.js": "Vue.js",
    "vuejs": "Vue.js",
    "angular": "Angular",
    "angular.js": "Angular",
    "angularjs": "Angular",
    "svelte": "Svelte",
    
    # Web Styling & Markup
    "html": "HTML & CSS",
    "css": "HTML & CSS",
    "html5": "HTML & CSS",
    "css3": "HTML & CSS",
    "html & css": "HTML & CSS",
    "html/css": "HTML & CSS",
    "tailwind": "Tailwind CSS",
    "tailwind css": "Tailwind CSS",
    "tailwindcss": "Tailwind CSS",
    "bootstrap": "Bootstrap",
    "sass": "SASS/SCSS",
    "scss": "SASS/SCSS",
    
    # Python & Frameworks
    "python": "Python",
    "python3": "Python",
    "python 3": "Python",
    "py": "Python",
    "fastapi": "FastAPI",
    "fast api": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "go": "Go",
    "golang": "Go",
    
    # Databases & SQL
    "sql": "SQL & Databases",
    "sql & databases": "SQL & Databases",
    "database": "SQL & Databases",
    "databases": "SQL & Databases",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "sqlite": "SQLite",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "redis": "Redis",
    
    # Data Science & Machine Learning
    "machine learning": "Machine Learning (Scikit-Learn)",
    "machine learning (scikit-learn)": "Machine Learning (Scikit-Learn)",
    "ml": "Machine Learning (Scikit-Learn)",
    "scikit-learn": "Machine Learning (Scikit-Learn)",
    "sklearn": "Machine Learning (Scikit-Learn)",
    "pandas": "Pandas & Data Manipulation",
    "pandas & data manipulation": "Pandas & Data Manipulation",
    "numpy": "NumPy",
    "data science": "Data Science",
    "data analysis": "Data Analytics",
    "deep learning": "Deep Learning",
    "tensorflow": "TensorFlow / PyTorch",
    "pytorch": "TensorFlow / PyTorch",
    "tensorflow / pytorch": "TensorFlow / PyTorch",
    "statistics": "Statistics & Mathematics",
    "statistics & mathematics": "Statistics & Mathematics",
    "data visualization": "Data Visualization & Dashboards",
    "data visualization & dashboards": "Data Visualization & Dashboards",
    
    # DevOps, Cloud & Tools
    "docker": "Docker & Containers",
    "docker & containers": "Docker & Containers",
    "containers": "Docker & Containers",
    "containerization": "Docker & Containers",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "linux": "Linux & Bash",
    "bash": "Linux & Bash",
    "shell": "Linux & Bash",
    "linux & bash": "Linux & Bash",
    "ci/cd": "CI/CD Pipelines",
    "ci/cd pipelines": "CI/CD Pipelines",
    "continuous integration": "CI/CD Pipelines",
    "github actions": "GitHub Actions",
    "git": "Git",
    "aws": "Cloud Fundamentals (AWS/GCP)",
    "gcp": "Cloud Fundamentals (AWS/GCP)",
    "azure": "Cloud Fundamentals (AWS/GCP)",
    "cloud": "Cloud Fundamentals (AWS/GCP)",
    "cloud fundamentals (aws/gcp)": "Cloud Fundamentals (AWS/GCP)",
    
    # API & Architecture
    "rest": "RESTful API Design",
    "rest api": "RESTful API Design",
    "rest apis": "RESTful API Design",
    "restful": "RESTful API Design",
    "restful api": "RESTful API Design",
    "restful api design": "RESTful API Design",
    "graphql": "GraphQL",
    "microservices": "Microservices",
    
    # QA & Testing
    "testing": "Software Testing Principles",
    "software testing principles": "Software Testing Principles",
    "test automation": "Test Automation",
    "jest": "Testing (Jest/Cypress)",
    "cypress": "Testing (Jest/Cypress)",
    "testing (jest/cypress)": "Testing (Jest/Cypress)",
    "pytest": "Pytest",
    
    # Security
    "cybersecurity": "Cybersecurity",
    "security": "Cybersecurity",
    "network security & protocols": "Network Security & Protocols",
    "network security": "Network Security & Protocols",
    "authentication & cryptography": "Authentication & Cryptography",
    "cryptography": "Authentication & Cryptography",
}

class SkillNormalizer:
    """Provides authoritative normalization, alias mapping, and comparison for technical skills."""

    @classmethod
    def clean_token(cls, skill: str) -> str:
        """Strips formatting, extra spaces, and common suffix noise."""
        if not skill:
            return ""
        s = skill.strip().lower()
        # Collapse multiple whitespace
        s = re.sub(r"\s+", " ", s)
        # Remove trailing periods or commas
        s = s.strip(".,;/")
        return s

    @classmethod
    def normalize(cls, skill: str) -> str:
        """
        Maps a skill name or alias to its canonical representation.
        If unknown, returns Title-cased cleaned skill name.
        """
        cleaned = cls.clean_token(skill)
        if not cleaned:
            return ""
        
        # Exact canonical alias lookup
        if cleaned in CANONICAL_SKILL_MAP:
            return CANONICAL_SKILL_MAP[cleaned]
        
        # Check without punctuation (e.g., 'react-native' -> 'react native')
        punct_stripped = re.sub(r"[-_/]+", " ", cleaned)
        if punct_stripped in CANONICAL_SKILL_MAP:
            return CANONICAL_SKILL_MAP[punct_stripped]
        
        # Fallback to trimmed original title casing
        return skill.strip()

    @classmethod
    def are_skills_equivalent(cls, skill_a: str, skill_b: str) -> bool:
        """Checks if two skill strings represent the same technical skill."""
        if not skill_a or not skill_b:
            return False
            
        norm_a = cls.normalize(skill_a)
        norm_b = cls.normalize(skill_b)
        
        if norm_a.lower() == norm_b.lower():
            return True
            
        clean_a = cls.clean_token(skill_a)
        clean_b = cls.clean_token(skill_b)
        
        # Substring / combined matching (e.g., 'React' in 'React & Redux', or 'HTML' in 'HTML & CSS')
        if clean_a == clean_b:
            return True
            
        # Specific combined parent/child rules:
        # e.g., if required skill is 'HTML & CSS', student having 'HTML' or 'CSS' or 'HTML5' matches
        html_css_family = {"html", "css", "html5", "css3", "html & css", "html/css"}
        if clean_a in html_css_family and clean_b in html_css_family:
            return True
            
        # SQL family
        sql_family = {"sql", "postgresql", "postgres", "mysql", "sqlite", "sql & databases"}
        if clean_a in sql_family and clean_b in sql_family:
            return True
            
        # Docker family
        docker_family = {"docker", "containers", "docker & containers", "containerization"}
        if clean_a in docker_family and clean_b in docker_family:
            return True
            
        # ML family
        ml_family = {"machine learning", "ml", "scikit-learn", "sklearn", "machine learning (scikit-learn)"}
        if clean_a in ml_family and clean_b in ml_family:
            return True
            
        # Linux family
        linux_family = {"linux", "bash", "shell", "linux & bash"}
        if clean_a in linux_family and clean_b in linux_family:
            return True

        return False

    @classmethod
    def match_skill_against_collection(
        cls, target_skill: str, candidate_skills: Dict[str, float]
    ) -> Tuple[bool, Optional[str], float]:
        """
        Matches target_skill against candidate_skills dictionary.
        Returns: (is_matched, matched_candidate_skill_name, score)
        """
        for cand_name, score in candidate_skills.items():
            if cls.are_skills_equivalent(target_skill, cand_name):
                return True, cand_name, score
        return False, None, 0.0
