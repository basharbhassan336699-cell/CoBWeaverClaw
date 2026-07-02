"""مخططات أدوات الذاكرة المتاحة للوكيل."""

MEMORY_TOOL_SCHEMAS = [
    {
        "name": "memory_add",
        "description": (
            "احفظ معلومة في الذاكرة. "
            "context: general|trading|academic|technical. "
            "write_level: auto=فوري | confirm=يطلب موافقة | permanent=لا يُحذف."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content":     {"type": "string"},
                "context":     {"type": "string", "enum": ["general","trading","academic","technical"]},
                "write_level": {"type": "string", "enum": ["auto","confirm","permanent"]},
                "weight":      {"type": "number", "default": 1.0},
            },
            "required": ["content"],
        },
    },
    {
        "name": "memory_delete",
        "description": "احذف ذكرى بمعرفها. لا يعمل على permanent.",
        "parameters": {
            "type": "object",
            "properties": {"id": {"type": "integer"}},
            "required": ["id"],
        },
    },
    {
        "name": "memory_list",
        "description": "اعرض ذكريات سياق معين مع أوزانها.",
        "parameters": {
            "type": "object",
            "properties": {
                "context": {"type": "string", "enum": ["general","trading","academic","technical"]}
            },
            "required": ["context"],
        },
    },
    {
        "name": "memory_prune",
        "description": "احذف الذكريات الضعيفة تلقائياً. يُستدعى من dreaming.",
        "parameters": {
            "type": "object",
            "properties": {"threshold": {"type": "number", "default": 0.1}},
        },
    },
]
