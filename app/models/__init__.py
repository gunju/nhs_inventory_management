"""
Import all models so Alembic autogenerate can discover them.
"""
from app.models.org import Trust, Hospital, Department, Ward  # noqa: F401
from app.models.user import User, Role, UserRoleAssignment  # noqa: F401
from app.models.product import (  # noqa: F401
    Supplier, Product, ProductAlias, UOM, CatalogItem,
    BarcodeIdentifier, ProductCategory,
)
from app.models.inventory import (  # noqa: F401
    InventoryLocation, StockBalance, StockMovement, StockAdjustment,
    PurchaseOrder, PurchaseOrderLine, GoodsReceipt, TransferOrder,
    ReorderPolicy, LeadTimeProfile, ConsumptionHistory, ExpiryBatchLot,
)
from app.models.ai import (  # noqa: F401
    DemandForecast, ForecastRun, ShortageRisk, OverstockRisk,
    RedistributionRecommendation, ReorderRecommendation,
    RecommendationDecision, AnomalyEvent, InsightSummary,
)
from app.models.rag import (  # noqa: F401
    DocumentSource, DocumentChunk, EmbeddingIndexRef,
    ConversationSession, ConversationMessage, CopilotAnswer,
)
from app.models.audit import (  # noqa: F401
    AuditLog, DataAccessLog, IntegrationRun, FailedIntegrationEvent,
    ModelDecisionLog, PromptTemplateVersion,
)
