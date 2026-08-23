"""数据模型测试（v3.2：project_groups → projects → charts → series）。"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import src.models  # noqa: F401
from src.core.database import Base
from src.models import ACTIVE, MISSING, Chart, Project, ProjectGroup, Series


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    S = sessionmaker(bind=engine, future=True)
    s = S()
    yield s
    s.close()


def test_four_level_crud(session):
    g = ProjectGroup(name="测试项目组", sort_order=0)
    session.add(g)
    session.flush()

    p = Project(name="LP G2 110W Performance", group_id=g.id,
                source_file_path=r"D:\data\out.xlsx",
                data_start_row=17, data_end_row=4195,
                data_start_col_letter="A", data_end_col_letter="AM",
                status=ACTIVE)
    session.add(p)
    session.flush()

    c = Chart(project_id=p.id, chart_name="功率 vs 电压",
              x_axis_label="电压 (V)", y_axis_label="功率 (W)",
              x_axis_major_unit=5, x_axis_minor_unit=1,
              show_grid=True, connect_line=True)
    session.add(c)
    session.flush()

    session.add(Series(chart_id=c.id, series_name="低功率系列",
                       x_col_letter="A", y_col_letter="F",
                       row_start=19, row_end=100,
                       color_hex="#FF0000", marker_shape="circle"))
    session.commit()

    loaded = session.query(ProjectGroup).one()
    assert loaded.projects[0].charts[0].chart_name == "功率 vs 电压"
    assert loaded.projects[0].charts[0].series_list[0].row_start == 19
    assert loaded.projects[0].charts[0].x_axis_major_unit == 5


def test_cascade_group_delete(session):
    g = ProjectGroup(name="G")
    session.add(g)
    session.flush()
    p = Project(name="P", group_id=g.id, source_file_path="x.xlsx", data_start_row=1)
    session.add(p)
    session.flush()
    c = Chart(project_id=p.id, chart_name="C1")
    session.add(c)
    session.flush()
    session.add(Series(chart_id=c.id, series_name="s", x_col_letter="A",
                       y_col_letter="B", row_start=2, row_end=50, color_hex="#0000FF"))
    session.commit()

    session.delete(g)
    session.commit()
    assert session.query(Project).count() == 0
    assert session.query(Chart).count() == 0
    assert session.query(Series).count() == 0


def test_status_values(session):
    g = ProjectGroup(name="G2")
    session.add(g)
    session.flush()
    session.add(Project(name="P2", group_id=g.id, source_file_path="x.xlsx",
                        data_start_row=1, status=MISSING))
    session.commit()
    assert session.query(Project).one().status == MISSING
