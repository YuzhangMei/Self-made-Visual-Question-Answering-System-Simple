import uuid

# 简单的内存 session 存储（Phase 1 用）
# 生产环境应使用 Redis / DB
SESSIONS = {}

def create_session(data):
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = data
    return session_id

def get_session(session_id):
    return SESSIONS.get(session_id)

def update_session(session_id, data):
    if session_id in SESSIONS:
        SESSIONS[session_id].update(data)
