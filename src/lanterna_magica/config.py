from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="LANTERNA",
    settings_files=["settings.toml", ".secrets.toml"],
    environments=True,
    env_switcher="LANTERNA_ENV",
    default_env="default",
)
