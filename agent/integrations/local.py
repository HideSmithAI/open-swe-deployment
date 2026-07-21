import os

from deepagents.backends import LocalShellBackend


class _LocalSandboxEnvironment(dict[str, str]):
    """Resolve run-scoped GitHub credentials immediately before each command."""

    _GIT_CONFIG = (
        ("credential.https://github.com.helper", "!gh auth git-credential"),
        ("url.https://github.com/.insteadOf", "git@github.com:"),
        ("url.https://github.com/.insteadOf", "ssh://git@github.com/"),
        ("url.https://github.com/.insteadOf", "git://github.com/"),
    )

    def __init__(self, base_env: dict[str, str]) -> None:
        super().__init__(base_env)
        self._github_token: str | None = None

    def set_github_token(self, token: str) -> None:
        self._github_token = token

    def items(self):  # type: ignore[override]
        env = dict.copy(self)
        token = self._github_token
        if token:
            env["OPEN_SWE_GITHUB_TOKEN"] = token
            env["GH_TOKEN"] = token
            try:
                config_index = int(env.get("GIT_CONFIG_COUNT", "0"))
            except ValueError:
                config_index = 0
            for key, value in self._GIT_CONFIG:
                env[f"GIT_CONFIG_KEY_{config_index}"] = key
                env[f"GIT_CONFIG_VALUE_{config_index}"] = value
                config_index += 1
            env["GIT_CONFIG_COUNT"] = str(config_index)
        return env.items()


class LocalAuthenticatedShellBackend(LocalShellBackend):
    """Local backend with a credential slot isolated to one Open SWE thread."""

    def set_github_token(self, token: str) -> None:
        env = self._env  # noqa: SLF001
        if not isinstance(env, _LocalSandboxEnvironment):
            raise TypeError("Local sandbox environment is not credential-aware")
        env.set_github_token(token)


def configure_local_sandbox_github_token(backend: object, token: str) -> None:
    """Bind a short-lived GitHub token to one local sandbox backend."""
    if isinstance(backend, LocalAuthenticatedShellBackend):
        backend.set_github_token(token)


def create_local_sandbox(sandbox_id: str | None = None):
    """Create a local shell sandbox with no isolation.

    WARNING: This runs commands directly on the host machine with no sandboxing.
    Only use for local development with human-in-the-loop enabled.

    The root directory defaults to the current working directory and can be
    overridden via the LOCAL_SANDBOX_ROOT_DIR environment variable. It is
    created if it does not already exist.

    Args:
        sandbox_id: Ignored for local sandboxes; accepted for interface compatibility.

    Returns:
        LocalShellBackend instance implementing SandboxBackendProtocol.
    """
    root_dir = os.getenv("LOCAL_SANDBOX_ROOT_DIR", os.getcwd())
    os.makedirs(root_dir, exist_ok=True)

    base_env = dict(os.environ)
    # Never fall back to credentials from the host account. Local runs receive
    # only the short-lived token bound to their current execution context.
    for name in ("OPEN_SWE_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        base_env.pop(name, None)

    return LocalAuthenticatedShellBackend(
        root_dir=root_dir,
        virtual_mode=True,
        env=_LocalSandboxEnvironment(base_env),
        inherit_env=False,
    )
