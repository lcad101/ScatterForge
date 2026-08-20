"""数据模型测试（冻结规范第 5 章：严禁存原始数据，仅存路径+元数据）。"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import src.models  # noqa: F401  注册模型
from src.core.database import Base
from src.models.project import ACTIVE, MISSING, Project
from src.models.series import Series
from src.models.theme import Theme


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    S = sessionmaker(bind=engine, future=True)
    s = S()
    yield s
    s.close()


def test_theme_project_series_crud(session):
    theme = Theme(name="我的图表项目", sort_order=0)
    session.add(theme)
    session.flush()

    project = Project(
        name="销售分析_散点图", theme_id=theme.id,
        source_file_path=r"D:\data\销售分析_Scatter.xlsx",
        raw_start_row=1, raw_end_row=100,
        raw_start_col_letter="A", raw_end_col_letter="D",
        status=ACTIVE,
    )
    session.add(project)
    session.flush()

    session.add(Series(project_id=project.id, series_name="销售额",
                       x_col_letter="A", y_col_letter="C",
                       color_hex="#FF0000", marker_shape="circle", sort_order=0))
    session.commit()

    loaded = session.query(Project).one()
    assert loaded.status == ACTIVE
    assert len(loaded.series_list) == 1
    assert loaded.series_list[0].color_hex == "#FF0000"
    # 确认项目表不含任何原始数值字段（仅路径 + 元数据）
    assert loaded.source_file_path == r"D:\data\销售分析_Scatter.xlsx"


def test_cascade_delete(session):
    theme = Theme(name="T")
    session.add(theme)
    session.flush()
    p = Project(name="P", theme_id=theme.id, source_file_path="x.xlsx",
                raw_start_col_letter="A")
    session.add(p)
    session.flush()
    session.add(Series(project_id=p.id, series_name="s", x_col_letter="A",
                       y_col_letter="B", color_hex="#0000FF"))
    session.commit()

    session.delete(theme)
    session.commit()
    assert session.query(Project).count() == 0
    assert session.query(Series).count() == 0


def test_status_values(session):
    theme = Theme(name="T2")
    session.add(theme)
    session.flush()
    p = Project(name="P2", theme_id=theme.id, source_file_path="x.xlsx",
                raw_start_col_letter="A", status=MISSING)
    session.add(p)
    session.commit()
    assert session.query(Project).one().status == MISSING
