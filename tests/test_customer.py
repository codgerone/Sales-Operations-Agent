from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from sales_ops.business.models import Customer


def test_customer_round_trip(session):
    customer = Customer(name="Acme Instruments GmbH")
    assert customer.id is None and customer.created_at is None

    session.add(customer)
    session.commit()
    customer_id = customer.id
    session.expunge_all()  # 清空本地缓存，下面的查询一定从数据库读

    loaded = session.execute(select(Customer).where(Customer.id == customer_id)).scalar_one()

    assert loaded is not customer
    assert loaded.name == "Acme Instruments GmbH"
    assert isinstance(loaded.id, int)
    # created_at 由数据库生成，带时区，接近当前时刻。
    assert loaded.created_at.tzinfo is not None
    assert abs(datetime.now(UTC) - loaded.created_at) < timedelta(minutes=1)


def test_customer_ids_are_generated_by_database(session):
    a, b = Customer(name="A"), Customer(name="B")
    session.add_all([a, b])
    session.flush()
    assert a.id is not None and b.id is not None and a.id != b.id


def test_customer_name_is_required(session):
    session.add(Customer(name=None))
    with pytest.raises(IntegrityError, match="not-null"):
        session.flush()
