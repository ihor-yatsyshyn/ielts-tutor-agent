import pytest

from agent.llm import set_llm
from db import repo
from db.session import init_db


@pytest.fixture(autouse=True)
def fresh_db():
    init_db("sqlite:///:memory:")
    set_llm(None)
    yield
    set_llm(None)


@pytest.fixture
def student():
    return repo.get_or_create_student("alice")


@pytest.fixture
def student2():
    return repo.get_or_create_student("bob")
