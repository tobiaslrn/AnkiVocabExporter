from aqt import mw

DEFAULT_CONFIG = {
    "fields": [],
    "grouping": "status",
    "format": "json",
    "include_learning": True,
    "include_young": True,
    "include_mature": True,
    "last_export_dir": "",
    "predictive_days": 0,
}


def get_config() -> dict:
    config = mw.addonManager.getConfig(__name__.rsplit(".", 1)[0])
    if config is None:
        config = DEFAULT_CONFIG.copy()
    else:
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value
    return config


def save_config(config: dict) -> None:
    mw.addonManager.writeConfig(__name__.rsplit(".", 1)[0], config)
