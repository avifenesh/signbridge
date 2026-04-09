import asyncio

import pytest

from session import Session, SessionManager, State


def test_create_session():
    mgr = SessionManager(max_sessions=5)
    sess = mgr.create(chat_id=100)
    assert sess.chat_id == 100
    assert sess.state == State.JOINING
    assert isinstance(sess.id, str)
    assert len(sess.id) == 8


def test_get_session():
    mgr = SessionManager(max_sessions=5)
    sess = mgr.create(chat_id=200)
    assert mgr.get(sess.id) is sess
    assert mgr.get("nonexistent") is None


def test_remove_session():
    mgr = SessionManager(max_sessions=5)
    sess = mgr.create(chat_id=300)
    removed = mgr.remove(sess.id)
    assert removed is sess
    assert mgr.get(sess.id) is None
    assert mgr.remove(sess.id) is None


def test_list_all():
    mgr = SessionManager(max_sessions=5)
    s1 = mgr.create(chat_id=1)
    s2 = mgr.create(chat_id=2)
    listed = mgr.list_all()
    assert len(listed) == 2
    assert {s.id for s in listed} == {s1.id, s2.id}


def test_max_sessions_enforced():
    mgr = SessionManager(max_sessions=2)
    mgr.create(chat_id=1)
    mgr.create(chat_id=2)
    with pytest.raises(RuntimeError, match="max sessions"):
        mgr.create(chat_id=3)


def test_duplicate_chat_rejected():
    mgr = SessionManager(max_sessions=5)
    mgr.create(chat_id=42)
    with pytest.raises(RuntimeError, match="already active"):
        mgr.create(chat_id=42)


def test_duplicate_allowed_after_remove():
    mgr = SessionManager(max_sessions=5)
    sess = mgr.create(chat_id=42)
    mgr.remove(sess.id)
    sess2 = mgr.create(chat_id=42)
    assert sess2.id != sess.id


def test_session_to_dict():
    mgr = SessionManager(max_sessions=5)
    sess = mgr.create(chat_id=99)
    d = sess.to_dict()
    assert d["chat_id"] == 99
    assert d["state"] == "joining"
    assert "id" in d
    assert "created_at" in d


@pytest.mark.asyncio
async def test_close_all():
    mgr = SessionManager(max_sessions=5)
    s1 = mgr.create(chat_id=1)
    s2 = mgr.create(chat_id=2)
    await mgr.close_all()
    assert mgr.list_all() == []
    assert s1.stop_event.is_set()
    assert s2.stop_event.is_set()


@pytest.mark.asyncio
async def test_audio_queue_drop_when_full():
    sess = Session(id="test", chat_id=1)
    # Fill the queue
    for i in range(sess.audio_q.maxsize):
        sess.audio_q.put_nowait(b"\x00" * 640)
    # Next put should not raise — it should be caller's responsibility
    # (bridge drops via put_nowait + except QueueFull)
    with pytest.raises(asyncio.QueueFull):
        sess.audio_q.put_nowait(b"\x00" * 640)
