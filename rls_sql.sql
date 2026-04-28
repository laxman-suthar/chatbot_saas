-- ═══════════════════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY (RLS) FOR MULTI-TENANT ISOLATION
-- Run these SQL commands in Supabase SQL Editor
-- ═══════════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────────────────
-- 1. WEBSITES TABLE RLS
-- ─────────────────────────────────────────────────────────────────────────

ALTER TABLE websites_website ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own websites
CREATE POLICY "Users can only access their own websites"
ON websites_website
FOR SELECT
USING (owner_id = auth.uid());

-- Policy: Users can only update their own websites
CREATE POLICY "Users can only update their own websites"
ON websites_website
FOR UPDATE
USING (owner_id = auth.uid())
WITH CHECK (owner_id = auth.uid());

-- Policy: Users can only delete their own websites
CREATE POLICY "Users can only delete their own websites"
ON websites_website
FOR DELETE
USING (owner_id = auth.uid());

-- Policy: Users can only insert websites they own
CREATE POLICY "Users can only create websites"
ON websites_website
FOR INSERT
WITH CHECK (owner_id = auth.uid());


-- ─────────────────────────────────────────────────────────────────────────
-- 2. DOCUMENT TABLE RLS
-- ─────────────────────────────────────────────────────────────────────────

ALTER TABLE knowledge_base_document ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access documents from their own websites
CREATE POLICY "Users can only access their own documents"
ON knowledge_base_document
FOR SELECT
USING (
    website_id IN (
        SELECT id FROM websites_website 
        WHERE owner_id = auth.uid()
    )
);

-- Policy: Users can only insert documents to their own websites
CREATE POLICY "Users can only insert documents to their own websites"
ON knowledge_base_document
FOR INSERT
WITH CHECK (
    website_id IN (
        SELECT id FROM websites_website 
        WHERE owner_id = auth.uid()
    )
);

-- Policy: Users can only update documents from their own websites
CREATE POLICY "Users can only update their own documents"
ON knowledge_base_document
FOR UPDATE
USING (
    website_id IN (
        SELECT id FROM websites_website 
        WHERE owner_id = auth.uid()
    )
)
WITH CHECK (
    website_id IN (
        SELECT id FROM websites_website 
        WHERE owner_id = auth.uid()
    )
);

-- Policy: Users can only delete documents from their own websites
CREATE POLICY "Users can only delete their own documents"
ON knowledge_base_document
FOR DELETE
USING (
    website_id IN (
        SELECT id FROM websites_website 
        WHERE owner_id = auth.uid()
    )
);


-- ─────────────────────────────────────────────────────────────────────────
-- 3. DOCUMENT CHUNK TABLE RLS (pgvector embeddings)
-- ─────────────────────────────────────────────────────────────────────────

ALTER TABLE knowledge_base_documentchunk ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only select chunks from their own websites
CREATE POLICY "Users can only access chunks from their own websites"
ON knowledge_base_documentchunk
FOR SELECT
USING (
    website_id IN (
        SELECT id FROM websites_website 
        WHERE owner_id = auth.uid()
    )
);

-- Policy: Users can only insert chunks to their own websites
CREATE POLICY "Users can only insert chunks to their own websites"
ON knowledge_base_documentchunk
FOR INSERT
WITH CHECK (
    website_id IN (
        SELECT id FROM websites_website 
        WHERE owner_id = auth.uid()
    )
);

-- Policy: Users can only delete chunks from their own websites
CREATE POLICY "Users can only delete chunks from their own websites"
ON knowledge_base_documentchunk
FOR DELETE
USING (
    website_id IN (
        SELECT id FROM websites_website 
        WHERE owner_id = auth.uid()
    )
);


-- ─────────────────────────────────────────────────────────────────────────
-- 4. CHAT TABLE RLS
-- ─────────────────────────────────────────────────────────────────────────

ALTER TABLE chat_chat ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access chats from their own websites
CREATE POLICY "Users can only access chats from their own websites"
ON chat_chat
FOR SELECT
USING (
    website_id IN (
        SELECT id FROM websites_website 
        WHERE owner_id = auth.uid()
    )
);

-- Policy: Users can only insert chats to their own websites
CREATE POLICY "Users can only create chats for their own websites"
ON chat_chat
FOR INSERT
WITH CHECK (
    website_id IN (
        SELECT id FROM websites_website 
        WHERE owner_id = auth.uid()
    )
);

-- Policy: Users can only delete chats from their own websites
CREATE POLICY "Users can only delete chats from their own websites"
ON chat_chat
FOR DELETE
USING (
    website_id IN (
        SELECT id FROM websites_website 
        WHERE owner_id = auth.uid()
    )
);


-- ─────────────────────────────────────────────────────────────────────────
-- 5. MESSAGE TABLE RLS
-- ─────────────────────────────────────────────────────────────────────────

ALTER TABLE chat_message ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access messages from their own chats
CREATE POLICY "Users can only access messages from their own chats"
ON chat_message
FOR SELECT
USING (
    chat_id IN (
        SELECT id FROM chat_chat 
        WHERE website_id IN (
            SELECT id FROM websites_website 
            WHERE owner_id = auth.uid()
        )
    )
);

-- Policy: Users can only insert messages to their own chats
CREATE POLICY "Users can only insert messages to their own chats"
ON chat_message
FOR INSERT
WITH CHECK (
    chat_id IN (
        SELECT id FROM chat_chat 
        WHERE website_id IN (
            SELECT id FROM websites_website 
            WHERE owner_id = auth.uid()
        )
    )
);


-- ═══════════════════════════════════════════════════════════════════════════
-- VERIFY RLS IS ENABLED
-- ═══════════════════════════════════════════════════════════════════════════

-- Check all tables have RLS enabled:
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN (
    'websites_website',
    'knowledge_base_document',
    'knowledge_base_documentchunk',
    'chat_chat',
    'chat_message'
);

-- Output should show: rowsecurity = true for all tables