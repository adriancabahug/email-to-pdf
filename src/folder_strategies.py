class FastFolderStrategy:
    SKIP = frozenset([
        "rss feeds",
        "sync issues",
        "junk email",
        "deleted items",
        "public folders",
        "archive",
        "drafts",
        "conversation history",
        "contacts",
        "calendar",
        "tasks",
        "notes",
        "journal",
        "outbox",
    ])

    PRIORITY = frozenset([
        "inbox",
        "sent items",
    ])

    def __call__(self, folder_name: str) -> bool:
        name = folder_name.lower().strip()
        return name in self.PRIORITY and name not in self.SKIP


class DeepFolderStrategy:
    SKIP = frozenset([
        "rss feeds",
        "sync issues",
    ])

    def __call__(self, folder_name: str) -> bool:
        return folder_name.lower().strip() not in self.SKIP
