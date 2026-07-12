from enum import Enum


class AILayerHealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    NO_DEPLOYMENTS = "no_deployments"

    def is_ready(self) -> bool:
        return self == AILayerHealthStatus.HEALTHY
