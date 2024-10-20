from flask import Flask, request, jsonify, send_file
from flask_restful import Api, Resource
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
api = Api(app)

# Database models
class Chatbot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    llm_model = db.Column(db.String(100), nullable=False)
    custom_instructions = db.Column(db.Text)
    tone = db.Column(db.String(50))
    humor_style = db.Column(db.String(50))
    personality = db.Column(db.String(100))
    knowledge_base = db.Column(db.String(200))
    language_mode = db.Column(db.String(50))
    response_style = db.Column(db.String(50))
    creativity_level = db.Column(db.String(50))

class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chatbot_id = db.Column(db.Integer, db.ForeignKey('chatbot.id'), nullable=False)
    messages = db.relationship('ChatMessage', backref='chat_session', lazy=True)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    is_user = db.Column(db.Boolean, nullable=False)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    tags = db.Column(db.String(200))
    overview = db.Column(db.Text)
    programming_language = db.Column(db.String(50))
    libraries = db.Column(db.String(200))
    notes = db.Column(db.Text)
    priority = db.Column(db.String(50))

# API Resources
class ChatbotResource(Resource):
    def get(self, chatbot_id=None):
        if chatbot_id:
            chatbot = Chatbot.query.get_or_404(chatbot_id)
            return jsonify(self.chatbot_to_dict(chatbot))
        chatbots = Chatbot.query.all()
        return jsonify([self.chatbot_to_dict(c) for c in chatbots])

    def post(self):
        data = request.json
        new_chatbot = Chatbot(**data)
        db.session.add(new_chatbot)
        db.session.commit()
        return jsonify(self.chatbot_to_dict(new_chatbot)), 201

    def chatbot_to_dict(self, chatbot):
        return {c.name: getattr(chatbot, c.name) for c in chatbot.__table__.columns}

class ChatSessionResource(Resource):
    def get(self, session_id):
        session = ChatSession.query.get_or_404(session_id)
        messages = [{'content': m.content, 'is_user': m.is_user, 'timestamp': m.timestamp} for m in session.messages]
        return jsonify({'session_id': session.id, 'chatbot_id': session.chatbot_id, 'messages': messages})

    def post(self):
        data = request.json
        new_session = ChatSession(chatbot_id=data['chatbot_id'])
        db.session.add(new_session)
        db.session.commit()
        return jsonify({'session_id': new_session.id}), 201

class ChatMessageResource(Resource):
    def post(self, session_id):
        data = request.json
        new_message = ChatMessage(session_id=session_id, content=data['content'], is_user=data['is_user'])
        db.session.add(new_message)
        db.session.commit()
        return jsonify({'message_id': new_message.id}), 201

class TaskResource(Resource):
    def get(self, task_id=None):
        if task_id:
            task = Task.query.get_or_404(task_id)
            return jsonify(self.task_to_dict(task))
        tasks = Task.query.all()
        return jsonify([self.task_to_dict(t) for t in tasks])

    def post(self):
        data = request.json
        new_task = Task(**data)
        db.session.add(new_task)
        db.session.commit()
        return jsonify(self.task_to_dict(new_task)), 201

    def task_to_dict(self, task):
        return {c.name: getattr(task, c.name) for c in task.__table__.columns}

class TaskPDFResource(Resource):
    def get(self):
        tasks = Task.query.all()
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        y = 750
        for task in tasks:
            p.drawString(100, y, f"Name: {task.name}")
            y -= 20
            p.drawString(100, y, f"Type: {task.type}")
            y -= 20
            p.drawString(100, y, f"Tags: {task.tags}")
            y -= 20
            p.drawString(100, y, f"Priority: {task.priority}")
            y -= 40
            if y < 100:
                p.showPage()
                y = 750
        p.save()
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name='tasks.pdf', mimetype='application/pdf')

# API routes
api.add_resource(ChatbotResource, '/api/chatbots', '/api/chatbots/<int:chatbot_id>')
api.add_resource(ChatSessionResource, '/api/chat_sessions', '/api/chat_sessions/<int:session_id>')
api.add_resource(ChatMessageResource, '/api/chat_sessions/<int:session_id>/messages')
api.add_resource(TaskResource, '/api/tasks', '/api/tasks/<int:task_id>')
api.add_resource(TaskPDFResource, '/api/tasks/pdf')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)