from __future__ import annotations

import json
import os
from datetime import datetime

from flask import (
    Flask,
    abort,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

from models import Subtask, Task, db


def create_app() -> Flask:
    app = Flask(__name__)

    db_path = os.environ.get(
        "TASK_DB_PATH",
        os.path.join(app.instance_path, "tasks.sqlite3"),
    )
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.update(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
    )

    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.context_processor
    def inject_sidebar_tasks():
        all_tasks = Task.query.order_by(
            Task.quadrant.asc(),
            Task.id.desc(),
        ).all()
        return {"sidebar_tasks": all_tasks}

    @app.get("/")
    def index():
        q = request.args.get("q", "").strip()
        quadrant_filter = request.args.get("quadrant")

        query = Task.query
        if quadrant_filter and quadrant_filter.isdigit():
            query = query.filter(Task.quadrant == int(quadrant_filter))

        if q:
            like = f"%{q}%"
            query = query.filter(
                db.or_(
                    Task.title.ilike(like),
                    Task.description.ilike(like),
                    Task.subtasks.any(
                        db.or_(
                            Subtask.title.ilike(like),
                            Subtask.description.ilike(like),
                        )
                    ),
                )
            )

        tasks = query.order_by(
            Task.quadrant.asc(),
            Task.id.desc(),
        ).all()
        return render_template(
            "index.html",
            tasks=tasks,
            search_query=q,
            quadrant_filter=quadrant_filter,
        )

    @app.get("/tasks/new")
    def task_new():
        return render_template("task_form.html", task=None)

    @app.post("/tasks/new")
    def task_create():
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        status = (request.form.get("status") or "planned").strip() or "planned"
        due_raw = (request.form.get("due_date") or "").strip()
        due_date = None
        if due_raw:
            try:
                due_date = datetime.strptime(due_raw, "%Y-%m-%d").date()
            except ValueError:
                due_date = None
        quadrant_raw = request.form.get("quadrant") or "2"
        try:
            quadrant = int(quadrant_raw)
        except ValueError:
            quadrant = 2
        quadrant = min(4, max(1, quadrant))
        if not title:
            return (
                render_template(
                    "task_form.html",
                    task=None,
                    error="Название задачи обязательно.",
                ),
                400,
            )

        task = Task(
            title=title,
            description=description,
            quadrant=quadrant,
            status=status,
            due_date=due_date,
        )
        db.session.add(task)
        db.session.commit()
        return redirect(url_for("task_view", task_id=task.id))

    @app.get("/tasks/<int:task_id>")
    def task_view(task_id: int):
        task = Task.query.get(task_id)
        if not task:
            abort(404)
        return render_template("task_view.html", task=task)

    @app.get("/tasks/<int:task_id>/edit")
    def task_edit(task_id: int):
        task = Task.query.get(task_id)
        if not task:
            abort(404)
        return render_template("task_form.html", task=task)

    @app.post("/tasks/<int:task_id>/edit")
    def task_update(task_id: int):
        task = Task.query.get(task_id)
        if not task:
            abort(404)

        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        status = (
            request.form.get("status") or task.status or "planned"
        ).strip() or "planned"
        due_raw = (request.form.get("due_date") or "").strip()
        due_date = task.due_date
        if due_raw:
            try:
                due_date = datetime.strptime(due_raw, "%Y-%m-%d").date()
            except ValueError:
                pass
        quadrant_raw = request.form.get("quadrant") or str(task.quadrant or 2)
        try:
            quadrant = int(quadrant_raw)
        except ValueError:
            quadrant = task.quadrant or 2
        quadrant = min(4, max(1, quadrant))
        if not title:
            return (
                render_template(
                    "task_form.html",
                    task=task,
                    error="Название задачи обязательно.",
                ),
                400,
            )

        task.title = title
        task.description = description
        task.status = status
        task.due_date = due_date
        task.quadrant = quadrant
        db.session.commit()
        return redirect(url_for("task_view", task_id=task.id))

    @app.post("/tasks/<int:task_id>/delete")
    def task_delete(task_id: int):
        task = Task.query.get(task_id)
        if not task:
            abort(404)
        db.session.delete(task)
        db.session.commit()
        return redirect(url_for("index"))

    @app.post("/tasks/<int:task_id>/subtasks/new")
    def subtask_create(task_id: int):
        task = Task.query.get(task_id)
        if not task:
            abort(404)

        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        if not title:
            return redirect(url_for("task_view", task_id=task.id))

        st = Subtask(task_id=task.id, title=title, description=description)
        db.session.add(st)
        db.session.commit()
        return redirect(url_for("task_view", task_id=task.id))

    @app.get("/subtasks/<int:subtask_id>/edit")
    def subtask_edit(subtask_id: int):
        st = Subtask.query.get(subtask_id)
        if not st:
            abort(404)
        return render_template("subtask_form.html", subtask=st)

    @app.post("/subtasks/<int:subtask_id>/edit")
    def subtask_update(subtask_id: int):
        st = Subtask.query.get(subtask_id)
        if not st:
            abort(404)

        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        status = (
            request.form.get("status") or st.status or "planned"
        ).strip() or "planned"
        quadrant_raw = request.form.get("quadrant") or str(st.quadrant or 2)
        due_raw = (request.form.get("due_date") or "").strip()
        due_date = st.due_date
        if due_raw:
            try:
                due_date = datetime.strptime(due_raw, "%Y-%m-%d").date()
            except ValueError:
                pass
        is_done = request.form.get("is_done") == "on"
        if not title:
            return (
                render_template(
                    "subtask_form.html",
                    subtask=st,
                    error="Название подзадачи обязательно.",
                ),
                400,
            )

        st.title = title
        st.description = description
        st.status = status
        st.quadrant = (
            int(quadrant_raw) if quadrant_raw and quadrant_raw.isdigit() else st.quadrant
        )
        st.due_date = due_date
        st.is_done = is_done
        db.session.commit()
        return redirect(url_for("task_view", task_id=st.task_id))

    @app.post("/subtasks/<int:subtask_id>/toggle")
    def subtask_toggle(subtask_id: int):
        st = Subtask.query.get(subtask_id)
        if not st:
            abort(404)
        st.is_done = not st.is_done
        db.session.commit()
        return redirect(url_for("task_view", task_id=st.task_id))

    @app.post("/subtasks/<int:subtask_id>/delete")
    def subtask_delete(subtask_id: int):
        st = Subtask.query.get(subtask_id)
        if not st:
            abort(404)
        task_id = st.task_id
        db.session.delete(st)
        db.session.commit()
        return redirect(url_for("task_view", task_id=task_id))

    @app.get("/export")
    def export_json():
        tasks = Task.query.order_by(Task.id.asc()).all()
        payload = []
        for t in tasks:
            payload.append(
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "quadrant": t.quadrant,
                    "status": t.status,
                    "due_date": (
                        t.due_date.isoformat()
                        if t.due_date
                        else None
                    ),
                    "created_at": t.created_at.isoformat(),
                    "subtasks": [
                        {
                            "id": s.id,
                            "title": s.title,
                            "description": s.description,
                            "is_done": s.is_done,
                            "quadrant": s.quadrant,
                            "status": s.status,
                            "due_date": (
                                s.due_date.isoformat()
                                if s.due_date
                                else None
                            ),
                            "created_at": s.created_at.isoformat(),
                        }
                        for s in t.subtasks
                    ],
                }
            )

        resp = make_response(json.dumps(payload, ensure_ascii=False, indent=2))
        resp.mimetype = "application/json; charset=utf-8"
        resp.headers["Content-Disposition"] = (
            "attachment; filename=tasks_export.json"
        )
        return resp

    @app.post("/import")
    def import_json():
        raw = (request.form.get("data") or "").strip()
        if not raw:
            return redirect(url_for("index"))

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return (
                render_template(
                    "index.html",
                    tasks=Task.query.all(),
                    error="Не удалось прочитать JSON.",
                ),
                400,
            )

        Task.query.delete()
        db.session.flush()

        for t in data:
            due = t.get("due_date")
            due_date = None
            if due:
                try:
                    due_date = datetime.fromisoformat(due).date()
                except ValueError:
                    due_date = None
            task = Task(
                title=t.get("title", ""),
                description=t.get("description", "") or "",
                quadrant=int(t.get("quadrant") or 2),
                status=t.get("status") or "planned",
                due_date=due_date,
            )
            db.session.add(task)
            db.session.flush()

            for s in t.get("subtasks", []):
                sdue = s.get("due_date")
                sdue_date = None
                if sdue:
                    try:
                        sdue_date = datetime.fromisoformat(sdue).date()
                    except ValueError:
                        sdue_date = None
                sub = Subtask(
                    task_id=task.id,
                    title=s.get("title", ""),
                    description=s.get("description", "") or "",
                    is_done=bool(s.get("is_done")),
                    quadrant=int(s.get("quadrant") or 2),
                    status=s.get("status") or "planned",
                    due_date=sdue_date,
                )
                db.session.add(sub)

        db.session.commit()
        return redirect(url_for("index"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
