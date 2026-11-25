"""数据库访问：Engine、Session 工厂与 ORM 基类。

模块导入时不连接数据库、不读配置；调用方传入地址创建 Engine，测试可以指向测试库。

会话用法：一次操作一个 Session，事务由 `s.begin()` 包住，正常退出提交、异常回滚：

    with factory() as s, s.begin():
        s.add(...)
"""

from sqlalchemy import Engine, MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# 约束命名约定：所有环境里约束名一致，迁移中才能按名修改或删除约束。
NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "ix": "ix_%(column_0_N_label)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


CONNECT_TIMEOUT_SECONDS = 5


def create_engine_from(url: str) -> Engine:
    # 连接超时：数据库不可达时尽快失败，而不是无限等待。
    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS},
    )


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
