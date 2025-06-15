import src.config.env.var_names
import src.config.env.env


def is_admin(tg_id: int) -> bool:
    return tg_id == int(
        src.config.env.env.get_env_var(
            src.config.env.var_names.ADMIN_ID
        )
    )
