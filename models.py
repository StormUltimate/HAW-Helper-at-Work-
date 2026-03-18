from __future__ import annotations

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    # 1-4: квадранты Эйзенхауэра (1=срочно/важно, 4=не срочно/не важно)
    quadrant = db.Column(db.Integer, nullable=False, default=2)
    status = db.Column(db.String(20), nullable=False, default="planned")
    due_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    subtasks = db.relationship(
        "Subtask",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by=(
            "Subtask.is_done.asc(), "
            "Subtask.due_date.asc().nullslast(), "
            "Subtask.quadrant.asc(), "
            "Subtask.id.asc()"
        ),
    )


class Subtask(db.Model):
    __tablename__ = "subtasks"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(
        db.Integer,
        db.ForeignKey("tasks.id"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    is_done = db.Column(db.Boolean, nullable=False, default=False)
    # Локальный приоритет подзадачи
    quadrant = db.Column(db.Integer, nullable=False, default=2)
    status = db.Column(db.String(20), nullable=False, default="planned")
    due_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    task = db.relationship("Task", back_populates="subtasks")
