"""Configuration system for Career Coach AI using dataclasses and YAML."""

import os
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class UserConfig:
    """User-specific configuration."""
    name: str
    data_directory: str

    def __post_init__(self):
        # Convert string to Path and auto-generate current date
        self.data_directory = Path(self.data_directory)
        self.current_date = datetime.now().strftime("%B %d, %Y")


@dataclass
class AgentConfig:
    """Core agent configuration."""
    name: str
    model: str
    instructions_template: str
    output_type: str

    def __post_init__(self):
        # Convert string to Path and validate
        self.instructions_template = Path(self.instructions_template)
        if not self.instructions_template.exists():
            raise FileNotFoundError(f"Instructions template not found: {self.instructions_template}")


@dataclass
class JobSearchConfig:
    """Job search tool configuration."""
    default_backend: str
    default_limit: int
    domains: List[str]
    timeout: int


@dataclass
class DocumentConfig:
    """Document processing configuration."""
    supported_extensions: List[str]
    encoding: str
    chunk_size: int
    max_file_size_mb: int


@dataclass
class InterfaceConfig:
    """Gradio interface configuration."""
    title: str
    description: str
    server_name: str
    server_port: int
    share: bool
    show_error: bool
    chatbot_height: int
    show_copy_button: bool
    show_copy_all_button: bool
    examples: List[str]


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str
    format: str
    disable_httpx_noise: bool


@dataclass
class SystemConfig:
    """Master configuration combining all sub-configurations."""
    user: UserConfig
    agent: AgentConfig
    job_search: JobSearchConfig
    documents: DocumentConfig
    interface: InterfaceConfig
    logging: LoggingConfig
    openai_api_key: Optional[str] = None

    def __post_init__(self):
        # Load OpenAI API key from environment if not provided
        if not self.openai_api_key:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")

    @classmethod
    def from_yaml(cls, config_path: Path = None) -> "SystemConfig":
        """Load configuration from YAML file."""
        if config_path is None:
            config_path = Path("config.yaml")

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, 'r') as f:
            yaml_data = yaml.safe_load(f)

        # Environment variable substitution
        yaml_data = cls._substitute_env_vars(yaml_data)

        # Create nested dataclass instances
        user_config = UserConfig(**yaml_data['user'])
        agent_config = AgentConfig(**yaml_data['agent'])
        job_search_config = JobSearchConfig(**yaml_data['job_search'])
        documents_config = DocumentConfig(**yaml_data['documents'])
        interface_config = InterfaceConfig(**yaml_data['interface'])
        logging_config = LoggingConfig(**yaml_data['logging'])

        return cls(
            user=user_config,
            agent=agent_config,
            job_search=job_search_config,
            documents=documents_config,
            interface=interface_config,
            logging=logging_config,
            openai_api_key=yaml_data.get('openai_api_key')
        )

    @staticmethod
    def _substitute_env_vars(data):
        """Recursively substitute environment variables in configuration data."""
        if isinstance(data, dict):
            return {key: SystemConfig._substitute_env_vars(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [SystemConfig._substitute_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
            # Extract environment variable name and default value
            env_expr = data[2:-1]  # Remove ${ and }
            if ":" in env_expr:
                env_name, default_value = env_expr.split(":", 1)
                return os.getenv(env_name, default_value)
            else:
                return os.getenv(env_expr, data)
        else:
            return data

    def get_full_description(self) -> str:
        """Get full interface description with current date."""
        return f"{self.interface.description}\n\n**Today is {self.user.current_date}**"


# Global configuration instance
_config: Optional[SystemConfig] = None


def load_config(config_path: Path = None) -> SystemConfig:
    """Load and return the global configuration instance."""
    global _config
    _config = SystemConfig.from_yaml(config_path)
    return _config


def get_config() -> SystemConfig:
    """Get the global configuration instance, loading default if not already loaded."""
    global _config
    if _config is None:
        _config = load_config()
    return _config