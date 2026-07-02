from datetime import datetime
import uuid
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum
import enum

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'pbl_secret_key' 
db = SQLAlchemy(app)

# ==============================================================================
# データモデルの定義
# ==============================================================================
class DayOfWeek(enum.Enum):
    MONDAY = "月曜日"
    TUESDAY = "火曜日"
    WEDNESDAY = "水曜日"
    THURSDAY = "木曜日"
    FRIDAY = "金曜日"
    SATURDAY = "土曜日"
    SUNDAY = "日曜日"

class Priority(enum.Enum):
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(100), nullable=False)
    dayOfWeek = db.Column(Enum(DayOfWeek), nullable=False)
    isCompleted = db.Column(db.Boolean, default=False, nullable=False)
    priority = db.Column(Enum(Priority), nullable=False, default=Priority.MEDIUM)
    memo = db.Column(db.Text, nullable=True, default="")
    
    start_hour = db.Column(db.Integer, nullable=True)
    start_minute = db.Column(db.Integer, nullable=True)
    end_hour = db.Column(db.Integer, nullable=True)
    end_minute = db.Column(db.Integer, nullable=True)
    
    createdAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def toggleCompletion(self):
        self.isCompleted = not self.isCompleted

# ==============================================================================
# HTMLテンプレート（①週間画面：PC全画面・7曜日横並び版）
# ==============================================================================
WEEKLY_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>計画表アプリ（PC全画面版）</title>
    <style>
        body { font-family: sans-serif; background-color: #f0f2f5; margin: 0; padding: 20px; display: flex; justify-content: center; }
        .pc-screen { width: 100%; max-width: 1600px; background: white; border-radius: 16px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); padding: 20px; box-sizing: border-box; min-height: 850px; display: flex; flex-direction: column; position: relative; }
        h1 { font-size: 24px; text-align: center; color: #333; margin-top: 10px; margin-bottom: 15px; }
        .error-flash { background-color: #ffebe9; color: #ff3b30; border: 1px solid #ffc0c0; padding: 10px; border-radius: 8px; margin-bottom: 15px; font-size: 14px; }
        
        .form-box { background: #f8fafc; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px; }
        .form-container { display: flex; gap: 15px; align-items: flex-end; }
        .form-group { flex: 1; }
        .form-group-full { flex: 2; }
        label { display: block; font-size: 12px; color: #64748b; margin-bottom: 4px; font-weight: bold; }
        input[type="text"], select { width: 100%; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 6px; box-sizing: border-box; font-size: 14px; }
        
        button.btn-submit { padding: 8px 20px; background-color: #007aff; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 14px; height: 38px; }
        
        .weekly-container { 
            flex-grow: 1; 
            display: grid;
            grid-template-columns: repeat(7, 1fr); 
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .day-section { 
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            min-width: 0; 
        }
        
        .day-inner {
            background: #fff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: 0 2px 5px rgba(0,0,0,0.02);
            min-height: 500px;
        }
        
        .day-header { background: #f1f5f9; padding: 10px; font-size: 14px; font-weight: bold; color: #334155; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; }
        .timetable-link { font-size: 11px; color: #007aff; text-decoration: none; font-weight: normal; }
        .task-count { font-size: 11px; background: #cbd5e1; padding: 1px 6px; border-radius: 10px; color: #475569; }
        
        .day-content { padding: 8px; flex-grow: 1; overflow-y: auto; background: #fafafa; }
        .no-tasks { font-size: 12px; color: #94a3b8; text-align: center; margin: 30px 0; }
        
        .task-wrapper { background: #fff; border-radius: 8px; margin-bottom: 8px; border: 1px solid #e2e8f0; border-left: 4px solid #3b82f6; overflow: hidden; cursor: pointer; box-shadow: 0 1px 3px rgba(0,0,0,0.02); }
        .task-wrapper:hover { background: #f8fafc; }
        
        .task-wrapper.priority-HIGH { border-left-color: #ef4444; }
        .task-wrapper.priority-LOW { border-left-color: #10b981; }
        .task-wrapper.completed { border-left-color: #94a3b8; opacity: 0.5; background: #f1f5f9; }
        .task-wrapper.completed .task-title { text-decoration: line-through; color: #64748b; }

        .task-item { display: flex; align-items: center; padding: 8px; font-size: 12px; justify-content: space-between; }
        .task-left { display: flex; align-items: center; flex-grow: 1; min-width: 0; }
        .task-checkbox { margin-right: 6px; transform: scale(1.0); cursor: pointer; flex-shrink: 0; }
        .task-info { display: flex; flex-direction: column; align-items: flex-start; flex-grow: 1; padding-right: 4px; min-width: 0; gap: 2px; }
        .task-title { word-break: break-all; color: #1e293b; line-height: 1.3; font-weight: 500; }
        .badge-row { display: flex; gap: 4px; flex-wrap: wrap; align-items: center; }
        .time-badge { font-size: 9px; color: #475569; background: #e2e8f0; padding: 1px 4px; border-radius: 4px; flex-shrink: 0; }
        .priority-badge { font-size: 9px; padding: 1px 4px; border-radius: 4px; background: #e2e8f0; color: #475569; flex-shrink: 0; }
        
        .btn-delete { background: none; border: none; color: #cbd5e1; font-size: 13px; cursor: pointer; padding: 2px; flex-shrink: 0; }
        .btn-delete:hover { color: #ef4444; }

        /* 📝 メモエリアのスタイルをテキストファイル風に改良 */
        .memo-box { background: #fffdf5; padding: 6px; border-top: 1px dashed #e2e8f0; font-size: 11px; display: none; }
        .memo-textarea { 
            width: 100%; 
            height: 60px; 
            resize: vertical; 
            box-sizing: border-box; 
            border: 1px solid #e2e8f0; 
            border-radius: 4px; 
            padding: 4px; 
            font-size: 11px; 
            font-family: inherit;
            background-color: #fffdf5;
            line-height: 1.4;
        }
        .memo-textarea:focus {
            outline: none;
            border-color: #f59e0b;
            background-color: #ffffff;
        }
        .memo-status {
            text-align: right;
            font-size: 9px;
            color: #94a3b8;
            margin-top: 2px;
        }
        
        .hint-banner { text-align: center; font-size: 12px; color: #94a3b8; margin-bottom: 12px; font-weight: bold; }

        .move-menu-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.4); z-index: 100; justify-content: center; align-items: center; }
        .move-menu { background: white; width: 340px; border-radius: 12px; padding: 20px; box-sizing: border-box; box-shadow: 0 4px 15px rgba(0,0,0,0.15); }
        .move-menu-overlay.active { display: flex; }
        .move-menu-title { font-size: 14px; font-weight: bold; color: #475569; margin-bottom: 12px; text-align: center; }
        .move-btn-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 15px; }
        .btn-move-day { padding: 8px; background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 12px; font-weight: bold; color: #334155; cursor: pointer; text-align: center; }
        .btn-move-day:hover { background: #007aff; color: white; border-color: #007aff; }
        .btn-move-cancel { width: 100%; padding: 8px; background: #cbd5e1; color: #475569; border: none; border-radius: 6px; font-size: 12px; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>
    <div class="pc-screen">
        <h1>📅 週間予定管理（デスクトップ版）</h1>

        {% with messages = get_flashed_messages() %}
          {% if messages %}
            {% for message in messages %}
              <div class="error-flash">⚠️ {{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <div class="form-box">
            <form action="/add" method="POST" class="form-container">
                <div class="form-group form-group-full">
                    <label>タスク名</label>
                    <input type="text" name="title" placeholder="例：PBLのコードを書く" required>
                </div>
                <div class="form-group">
                    <label>曜日</label>
                    <select name="dayOfWeek">
                        {% for day in DayOfWeek %}
                        <option value="{{ day.name }}">{{ day.value }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="form-group">
                    <label>優先度</label>
                    <select name="priority">
                        {% for p in Priority %}
                        <option value="{{ p.name }}" {% if p.name == 'MEDIUM' %}selected{% endif %}>{{ p.value }}</option>
                        {% endfor %}
                    </select>
                </div>
                <button type="submit" class="btn-submit">予定を追加</button>
            </form>
        </div>

        <div class="hint-banner">👆 タスクをクリックすると、別の曜日への移動やメモの直接編集ができます</div>

        <div class="weekly-container">
            {% for day in DayOfWeek %}
            <div class="day-section" id="section-{{ day.name }}">
                <div class="day-inner">
                    <div class="day-header">
                        <span>{{ day.value }}</span>
                        <span class="task-count" id="count-{{ day.name }}">{{ weekly_tasks[day].__len__() }}件</span>
                        <a href="/timetable/{{ day.name }}" class="timetable-link">⏳ 24h ➔</a>
                    </div>
                    <div class="day-content" id="content-{{ day.name }}">
                        {% if weekly_tasks[day] %}
                            {% for task in weekly_tasks[day] %}
                            <div class="task-wrapper {% if task.isCompleted %}completed{% endif %} priority-{{ task.priority.name }}" 
                                 id="wrapper-{{ task.id }}" 
                                 onclick="openActionMenu('{{ task.id }}', '{{ task.title }}')">
                                <div class="task-item">
                                    <div class="task-left">
                                        <input type="checkbox" class="task-checkbox" 
                                               {% if task.isCompleted %}checked{% endif %}
                                               onclick="event.stopPropagation(); toggleCheck('{{ task.id }}')">
                                        <div class="task-info">
                                            <span class="task-title">{{ task.title }}</span>
                                            <div class="badge-row">
                                                {% if task.start_hour is not none and task.end_hour is not none %}
                                                <span class="time-badge">{{ "%02d"|format(task.start_hour) }}:{{ "%02d"|format(task.start_minute) }}〜</span>
                                                {% endif %}
                                                <span class="priority-badge">{{ task.priority.value }}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <button class="btn-delete" onclick="event.stopPropagation(); deleteTask('{{ task.id }}', '{{ day.name }}')">✕</button>
                                </div>
                                
                                <div class="memo-box" id="memobox-{{ task.id }}" onclick="event.stopPropagation();" {% if task.memo %}style="display: block;"{% endif %}>
                                    <textarea class="memo-textarea" 
                                              id="memoinput-{{ task.id }}" 
                                              placeholder="メモを入力（Ctrl+Enterまたは枠外クリックで保存）..."
                                              onblur="saveMemo('{{ task.id }}')"
                                              onkeydown="handleMemoKeydown(event, '{{ task.id }}')">{{ task.memo if task.memo else '' }}</textarea>
                                    <div class="memo-status" id="memostatus-{{ task.id }}"></div>
                                </div>
                            </div>
                            {% endfor %}
                        {% else %}
                            <div class="no-tasks">予定はありません</div>
                        {% endif %}
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>

        <div class="move-menu-overlay" id="moveMenuOverlay" onclick="closeActionMenu()">
            <div class="move-menu" onclick="event.stopPropagation();">
                <div class="move-menu-title" id="menuTaskTitle">タスクをどこに移動しますか？</div>
                <div class="move-btn-grid">
                    {% for day in DayOfWeek %}
                    <button class="btn-move-day" onclick="executeMove('{{ day.name }}')">{{ day.value[:1] }}</button>
                    {% endfor %}
                    <button class="btn-move-day" style="background: #e2e8f0;" onclick="toggleMemoDirect()">📝 メモ欄</button>
                </div>
                <button class="btn-move-cancel" onclick="closeActionMenu()">キャンセル</button>
            </div>
        </div>

    </div>

    <script>
        let currentSelectedTaskId = null;

        function openActionMenu(taskId, taskTitle) {
            currentSelectedTaskId = taskId;
            document.getElementById('menuTaskTitle').innerText = `「${taskTitle}」の操作`;
            document.getElementById('moveMenuOverlay').classList.add('active');
        }

        function closeActionMenu() {
            document.getElementById('moveMenuOverlay').classList.remove('active');
            currentSelectedTaskId = null;
        }

        function toggleMemoDirect() {
            if (!currentSelectedTaskId) return;
            const id = currentSelectedTaskId;
            closeActionMenu();
            const memoBox = document.getElementById('memobox-' + id);
            const textarea = document.getElementById('memoinput-' + id);
            
            if (memoBox.style.display === 'block' && !textarea.value.trim()) {
                memoBox.style.display = 'none';
            } else {
                memoBox.style.display = 'block';
                textarea.focus();
            }
        }

        function handleMemoKeydown(event, taskId) {
            if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
                event.preventDefault();
                document.getElementById('memoinput-' + taskId).blur(); 
            }
        }

        function executeMove(targetDay) {
            if (!currentSelectedTaskId) return;
            
            fetch('/move_task', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `task_id=${currentSelectedTaskId}&target_day=${targetDay}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    closeActionMenu();
                    window.location.reload();
                }
            });
        }

        function toggleCheck(taskId) {
            fetch('/toggle/' + taskId)
            .then(response => response.json())
            .then(data => {
                const wrapper = document.getElementById('wrapper-' + taskId);
                if (data.isCompleted) wrapper.classList.add('completed');
                else wrapper.classList.remove('completed');
            });
        }

        function saveMemo(taskId) {
            const inputVal = document.getElementById('memoinput-' + taskId).value;
            
            fetch('/save_memo/' + taskId, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'memo=' + encodeURIComponent(inputVal)
            })
            .then(response => response.json())
            .then(data => {
                const statusEl = document.getElementById('memostatus-' + taskId);
                if (statusEl) {
                    statusEl.innerText = '保存されました';
                    setTimeout(() => { statusEl.innerText = ''; }, 1500);
                }
            });
        }

        function deleteTask(taskId, dayName) {
            if(!confirm('この予定を削除しますか？')) return;
            fetch('/delete/' + taskId)
            .then(response => response.json())
            .then(data => {
                document.getElementById('wrapper-' + taskId).remove();
                window.location.reload();
            });
        }
    </script>
</body>
</html>
"""

# ==============================================================================
# HTMLテンプレート（②24時間タイムテーブル画面）
# ==============================================================================
TIMETABLE_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ day_value }}のタイムテーブル</title>
    <style>
        body { font-family: sans-serif; background-color: #f0f2f5; margin: 0; padding: 20px; display: flex; justify-content: center; }
        .phone-screen { width: 100%; max-width: 375px; background: white; border-radius: 30px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); padding: 20px; box-sizing: border-box; min-height: 700px; display: flex; flex-direction: column; }
        
        .header-nav { display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #007aff; padding-bottom: 10px; margin-bottom: 15px; }
        .btn-back { background: #007aff; color: white; border: none; padding: 6px 12px; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 12px; text-decoration: none; }
        h1 { font-size: 18px; color: #333; margin: 0; }

        .edit-modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.4); justify-content: center; align-items: center; z-index: 1000; }
        .modal-content { background: white; padding: 20px; border-radius: 16px; width: 300px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
        .modal-title { font-size: 14px; font-weight: bold; margin-bottom: 10px; color: #333; }
        .modal-row { margin-bottom: 12px; }
        .modal-row label { display: block; font-size: 11px; color: #64748b; margin-bottom: 4px; }
        .modal-row select { width: 45%; padding: 4px; font-size: 13px; }
        .modal-buttons { display: flex; gap: 8px; justify-content: flex-end; margin-top: 15px; }
        .btn-cancel { background: #cbd5e1; color: #475569; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; }
        .btn-save { background: #007aff; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: bold; }

        .timeline-container { flex-grow: 1; overflow-y: auto; padding-right: 4px; position: relative; background: #fff; border-radius: 8px; border: 1px solid #e2e8f0; }
        .hour-row { display: flex; height: 60px; border-bottom: 1px solid #f1f5f9; box-sizing: border-box; position: relative; }
        .hour-label { width: 50px; font-size: 12px; font-weight: bold; color: #64748b; text-align: center; border-right: 1px solid #e2e8f0; background: #f8fafc; line-height: 20px; padding-top: 2px; box-sizing: border-box; }
        .hour-space { flex-grow: 1; background: transparent; }

        .unscheduled-section { background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 10px; padding: 10px; margin-bottom: 15px; }
        .unscheduled-title { font-size: 12px; font-weight: bold; color: #475569; margin-bottom: 6px; display: flex; justify-content: space-between; }
        .unscheduled-list { display: flex; flex-direction: column; gap: 6px; }
        .unscheduled-item { background: #fff; border: 1px solid #e2e8f0; border-left: 4px solid #3b82f6; padding: 6px 10px; border-radius: 6px; font-size: 12px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; }
        .unscheduled-item:hover { background: #f1f5f9; }

        .timeline-card { position: absolute; left: 55px; right: 5px; background: #e0f2fe; border-left: 4px solid #0284c7; border-radius: 6px; padding: 4px 8px; font-size: 11px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); box-sizing: border-box; overflow: hidden; cursor: pointer; transition: opacity 0.2s; z-index: 10; }
        .timeline-card:hover { opacity: 0.9; }
        .timeline-card.priority-HIGH { background: #fee2e2; border-left-color: #ef4444; }
        .timeline-card.priority-LOW { background: #dcfce7; border-left-color: #10b981; }
        .card-time { font-size: 10px; color: #64748b; font-weight: bold; }
        .card-title { font-weight: bold; color: #1e293b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    </style>
</head>
<body>
    <div class="phone-screen">
        <div class="header-nav">
            <a href="/" class="btn-back">◀ 週間ビュー</a>
            <h1>⏳ {{ day_value }}の24h</h1>
            <div style="width: 70px;"></div>
        </div>

        <div class="unscheduled-section">
            <div class="unscheduled-title">
                <span>📌 時間未設定のタスク</span>
                <span style="font-size: 10px; color: #94a3b8;">クリックして時間をセット</span>
            </div>
            <div class="unscheduled-list">
                {% set ns = namespace(has_un=false) %}
                {% for task in tasks %}
                    {% if task.start_hour is none %}
                        {% set ns.has_un = true %}
                        <div class="unscheduled-item priority-{{ task.priority.name }}" onclick="openEditModal('{{ task.id }}', '{{ task.title }}', '', '', '', '')">
                            <span>{{ task.title }}</span>
                            <span style="color: #007aff; font-size: 11px;">設定 ➔</span>
                        </div>
                    {% endif %}
                {% endfor %}
                {% if not ns.has_un %}
                    <div style="font-size: 11px; color: #94a3b8; text-align: center;">未設定のタスクはありません</div>
                {% endif %}
            </div>
        </div>

        <div class="timeline-container">
            {% for hour in range(24) %}
            <div class="hour-row">
                <div class="hour-label">{{ "%02d"|format(hour) }}:00</div>
                <div class="hour-space"></div>
            </div>
            {% endfor %}

            {% for task in tasks %}
                {% if task.start_hour is not none and task.end_hour is not none %}
                    {% set top_pos = (task.start_hour * 60) + task.start_minute %}
                    {% set duration = ((task.end_hour * 60) + task.end_minute) - top_pos %}
                    {% if duration < 25 %}{% set duration = 25 %}{% endif %}
                    
                    <div class="timeline-card priority-{{ task.priority.name }}" 
                         style="top: {{ top_pos }}px; height: {{ duration }}px;"
                         onclick="openEditModal('{{ task.id }}', '{{ task.title }}', '{{ task.start_hour }}', '{{ task.start_minute }}', '{{ task.end_hour }}', '{{ task.end_minute }}')">
                        <div class="card-time">
                            {{ "%02d"|format(task.start_hour) }}:{{ "%02d"|format(task.start_minute) }}〜{{ "%02d"|format(task.end_hour) }}:{{ "%02d"|format(task.end_minute) }}
                        </div>
                        <div class="card-title">{{ task.title }}</div>
                    </div>
                {% endif %}
            {% endfor %}
        </div>
    </div>

    <div class="edit-modal" id="editModal">
        <div class="modal-content">
            <div class="modal-title" id="modalTaskTitle">タスクの時間設定</div>
            <form id="editForm" action="/update_time" method="POST">
                <input type="hidden" name="task_id" id="modalTaskId">
                
                <div class="modal-row">
                    <label>開始時間</label>
                    <select name="start_hour" id="modalStartHour">
                        {% for h in range(24) %}<option value="{{ h }}">{{ "%02d"|format(h) }}</option>{% endfor %}
                    </select> 時
                    <select name="start_minute" id="modalStartMinute">
                        {% for m in range(0, 60, 5) %}<option value="{{ m }}">{{ "%02d"|format(m) }}</option>{% endfor %}
                    </select> 分
                </div>

                <div class="modal-row">
                    <label>終了時間</label>
                    <select name="end_hour" id="modalEndHour">
                        {% for h in range(24) %}<option value="{{ h }}">{{ "%02d"|format(h) }}</option>{% endfor %}
                    </select> 時
                    <select name="end_minute" id="modalEndMinute">
                        {% for m in range(0, 60, 5) %}<option value="{{ m }}">{{ "%02d"|format(m) }}</option>{% endfor %}
                    </select> 分
                </div>

                <div class="modal-buttons">
                    <button type="button" class="btn-cancel" onclick="closeEditModal()">キャンセル</button>
                    <button type="submit" class="btn-save">時間を保存</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        function openEditModal(id, title, sh, sm, eh, em) {
            document.getElementById('modalTaskId').value = id;
            document.getElementById('modalTaskTitle').innerText = '⏳「' + title + '」の時間設定';
            document.getElementById('modalStartHour').value = sh !== '' ? sh : "9";
            document.getElementById('modalStartMinute').value = sm !== '' ? sm : "0";
            document.getElementById('modalEndHour').value = eh !== '' ? eh : "10";
            document.getElementById('modalEndMinute').value = em !== '' ? em : "0";
            document.getElementById('editModal').style.display = 'flex';
        }
        function closeEditModal() {
            document.getElementById('editModal').style.display = 'none';
        }
    </script>
</body>
</html>
"""

# ==============================================================================
# ルーティング（コントローラー処理）
# ==============================================================================
@app.route('/')
def index():
    all_tasks = Task.query.order_by(Task.createdAt.asc()).all()
    weekly_tasks = {day: [] for day in DayOfWeek}
    for task in all_tasks:
        weekly_tasks[task.dayOfWeek].append(task)
    return render_template_string(WEEKLY_TEMPLATE, weekly_tasks=weekly_tasks, DayOfWeek=DayOfWeek, Priority=Priority)

@app.route('/move_task', methods=['POST'])
def move_task():
    task_id = request.form.get('task_id')
    target_day_name = request.form.get('target_day')
    
    task = Task.query.get_or_404(task_id)
    task.dayOfWeek = DayOfWeek[target_day_name]
    db.session.commit()
    
    counts = {day.name: Task.query.filter_by(dayOfWeek=day).count() for day in DayOfWeek}
    return jsonify({'success': True, 'counts': counts})

@app.route('/timetable/<string:day_name>')
def timetable(day_name):
    day_enum = DayOfWeek[day_name]
    day_tasks = Task.query.filter_by(dayOfWeek=day_enum).all()
    return render_template_string(TIMETABLE_TEMPLATE, tasks=day_tasks, day_value=day_enum.value, day_name=day_name)

@app.route('/add', methods=['POST'])
def add_task():
    title = request.form.get('title')
    day_name = request.form.get('dayOfWeek')
    priority_name = request.form.get('priority')
    
    if not title or not title.strip():
        flash("タイトルを入力してください。")
        return redirect(url_for('index'))

    new_task = Task(
        title=title,
        dayOfWeek=DayOfWeek[day_name],
        priority=Priority[priority_name],
        start_hour=None, start_minute=None, end_hour=None, end_minute=None
    )
    db.session.add(new_task)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/update_time', methods=['POST'])
def update_time():
    task_id = request.form.get('task_id')
    sh = request.form.get('start_hour')
    sm = request.form.get('start_minute')
    eh = request.form.get('end_hour')
    em = request.form.get('end_minute')

    task = Task.query.get_or_404(task_id)
    start_num = int(sh) * 60 + int(sm)
    end_num = int(eh) * 60 + int(em)

    if start_num >= end_num:
        flash("終了時間は開始時間より後の時刻にしてください。")
        return redirect(url_for('timetable', day_name=task.dayOfWeek.name))

    task.start_hour = int(sh)
    task.start_minute = int(sm)
    task.end_hour = int(eh)
    task.end_minute = int(em)
    db.session.commit()
    return redirect(url_for('timetable', day_name=task.dayOfWeek.name))

@app.route('/toggle/<string:task_id>')
def toggle_task(task_id):
    task = Task.query.get_or_404(task_id)
    task.toggleCompletion()
    db.session.commit()
    return jsonify({'isCompleted': task.isCompleted})

@app.route('/save_memo/<string:task_id>', methods=['POST'])
def save_memo(task_id):
    task = Task.query.get_or_404(task_id)
    task.memo = request.form.get('memo', '')
    db.session.commit()
    return jsonify({'memo': task.memo})

@app.route('/delete/<string:task_id>')
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    day = task.dayOfWeek
    db.session.delete(task)
    db.session.commit()
    new_count = Task.query.filter_by(dayOfWeek=day).count()
    return jsonify({'success': True, 'new_count': new_count})

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)