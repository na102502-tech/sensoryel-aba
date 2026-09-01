import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "CHANGE-ME-IN-PRODUCTION")
database_url = os.environ.get("DATABASE_URL", "sqlite:///aba_program.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="therapist")
    active = db.Column(db.Boolean, default=True)
    def set_password(self, pw): self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)

class Child(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    birth_date = db.Column(db.String(20))
    start_date = db.Column(db.String(20))
    guardian_phone = db.Column(db.String(30))
    note = db.Column(db.Text)
    status = db.Column(db.String(20), default="이용중")
    therapist_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    therapist = db.relationship("User", foreign_keys=[therapist_id])

class ProgramState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey("child.id"), nullable=False)
    area_key = db.Column(db.String(40), nullable=False)
    item_index = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="미시작")
    memo = db.Column(db.Text)
    __table_args__ = (db.UniqueConstraint("child_id","area_key","item_index", name="uq_program_item"),)

class SessionRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey("child.id"), nullable=False)
    area_key = db.Column(db.String(40), nullable=False)
    item_index = db.Column(db.Integer, nullable=False)
    session_no = db.Column(db.Integer, nullable=False)
    record_date = db.Column(db.String(20), nullable=False)
    trials = db.Column(db.String(50), default="")
    therapist_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ProgramArea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    area_key = db.Column(db.String(40), unique=True, nullable=False)
    label = db.Column(db.String(120), nullable=False)
    sub = db.Column(db.String(200), default="")
    sort_order = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)

class ProgramItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    area_key = db.Column(db.String(40), nullable=False)
    item_index = db.Column(db.Integer, nullable=False)  # 기록 연결용 고정번호
    name = db.Column(db.Text, nullable=False)
    sort_order = db.Column(db.Integer, default=0)       # 화면 표시 순서
    active = db.Column(db.Boolean, default=True)
    __table_args__ = (db.UniqueConstraint("area_key","item_index", name="uq_program_master_item"),)

DEFAULT_PROGRAMS = {'learning': {'label': '1 학습준비', 'sub': 'A영역 협조와 강화제 효과', 'items': ['강화제를 제시하면, 그것을 수락', '선택 가능한 2개의 물건 중에서 강화제 선택', '비강화제 주시', '일반적인 물건을 제시하면, 그것을 가지고 가기', '강화제를 얻기 위한 반응', '교사가 통제하는 강화제에 반응', '다수의 교사들에게 반응', '학습자료와 같은 자극제들을 만지지 않고 기다리기', '지시를 받기 위해 교사에게 주목하기', '반응하기 전에 배열된 학습자료를 먼저 살펴보기', '지시가 주어지면 신속하게 반응', '다양한 강화제(최소 3개)', '간헐강화', '교사와의 상호작용에 의한 강화', '교사의 얼굴 표정과 목소리의 변화 관찰', '사회적 강화제에 대한 반응', '강화제의 지연에도 참을성 있게 기다리기', '과제 완수에 대하여 인정받기', '과제 성취 그 자체가 강화제 역할']}, 'matching': {'label': '2 매칭', 'sub': 'B영역 시각적 수행', 'items': ['1조각 삽입 퍼즐', '도형상자', '견본과 동일한 물건에 일치시키기', '물건을 그림에 일치시키기', '제시된 그림을 동일한 그림에 일치시키기', '그림을 물건에 일치시키기', '신속하고 정확하게 짝 맞추기', '종류별로 분류하기', '디자인된 그림 카드 위에 블록 올려 놓기', '삽입퍼즐 틀에 여러 개의 연결된 퍼즐 조각들을 맞추어 넣기', '모서리가 사각형인 퍼즐', '블록 디자인에 맞게 블록 배열하기', '시각적 모형에 맞게 정해진 순서대로 배열', '일정한 모양에 따라 위치가 정해진 여러 조각들로 구성된 퍼즐', '직소 퍼즐(Jigsaw Puzzle)', '연관된 그림에 일치시키기', '기능별로 분류', '특징별로 분류', '종류별로 분류', '주어진 순서로 일정시간 경과 후 재연', '일정시간 경과 후 견본 찾기', '일련의 순서 연장', '단순한 입체 모형 복제', '짝을 이루는 물건 함께 배열하기', '연속 배치', '그림 순서', '미로 찾기']}, 'motor': {'label': '3 동작모방', 'sub': '기존 + D영역 횟수·순서 항목', 'items': ['사물을 가지고 동작 모방(10/1array)', '포인팅하는 동작 모방', '손 무릎이나 예쁜손 동작 모방', '사물을 가지고 동작 모방(10/3array)', '대근육 동작 모방(5)', '소근육 동작 모방(3)', '대근육 동작 모방(10)', '대근육 동작 모방(20)', '동작의 횟수 모방', '거울 보며 대근육 동작 모방(20)', '사진 또는 그림 보고 동작 모방(20)', '영상을 보고 동작 모방(20)', '소근육 동작 모방(20)', '순서에 따라 물건 만지기', '시범 동작을 본 후 순서에 따라 물건 만지기 모방', '사물 1개로 연속된 2단계 동작 모방(10/1array)', '관련없는 사물 2개 터치 동작 모방(10/5array)', '사물을 가지고 2단계 동작 모방(10/1array)', '사물 없이 2단계 동작 모방(10)', '동작의 순서 모방', '사물을 가지고 3단계 동작 모방(10/1array)', '사물 없이 3단계 동작 모방(10)', '여러 물건을 사용하는 동작의 순서 모방', '교차 동작 또는 일어나서 동작모방(10)', '율동 모방(10)', '얼굴 표정 모방(4)']}, 'language': {'label': '4 언어모방', 'sub': '언어모방', 'items': ['양볼 문지르기, 인디언 아 동작 모방', '눈, 코, 입, 귀 포인팅 동작 모방', '볼, 코, 귀, 입술 검지로 잡기 동작 모방', '윗입술, 아랫입술, 치아, 혀 포인팅 동작 모방', '턱움직임 모방 (이딱딱, 입 크게 아, 이)', '혀움직임 모방(메롱, 좌우로, 위아래로, 왼쪽. 오른쪽, 위로, 아래로, 이 사이로, 볼 밀기)', '입술움직임 모방 (입술 안으로, 입술 내밀기, 입술 쩝쩝 소리내기, 입술 뽀뽀 소리내기)', '불어 날리기 동작 모방(5)', '불어 소리내기 동작 모방(5)', '음성 모방 1음절(아, 에, 이, 오, 우)', '음성 모방 1음절 길이 변형 (아 길게, 아 짧게)', '자음+모음 모방(15)', '친숙한 1-2음절 1단어 모방(20개)', '친숙한 3-4음절 1단어 모방(20개)', '동작 단어 모방(10개)', '2단어 모방(20개)', '3단어 모방 (20개)']}, 'discrimination': {'label': '5 변별', 'sub': '변별', 'items': ['가리키는 곳을 쳐다보며 포인팅', '가리키는 것을 건네줌', '가림막으로 가리고 같은 소리나는 사물 조작하여 소리내기(10/3array)', '아주 좋아하는 친밀한 것들에 대한 이름을 변별(4/3array)', '아이템 이름을 변별(6/3array)', '아이템 이름을 변별(8/3array)', '아이템 이름을 변별(10/3array)', '아이템 이름을 변별(20/3array)', '동물소리(5), 환경음(5) 변별(10/5array)', '아이템 이름을 변별(50/10array)', '기능과 관련된 동작 사진 변별(10/5array)', '색깔과 모양 변별(10/5array)', '아이템의 기능을 듣고 사물사진 변별(10/5array)', '아이템의 특징을 듣고 사물 사진 변별(10/10array)', '아이템의 범주를 듣고 사물 사진 변별(10/10array)', '있다, 없다 변별(2array)', '무슨, 어떤, 누구가 포함된 질문에 변별(25/10array)', '2가지를 듣고 변별(5set/10array)', '동작 이름을 듣고 동작 사진 변별(50/5array)', '아이템 이름 변별(직업, 장소 포함) (200)', '신체의 기능을 듣고 변별(6/6array)', '성별로 사람을 변별(여자/남자)', '위치 변별(8) (위, 아래, 안, 밖, 앞, 뒤, 옆, 사이)', '같다, 다르다 변별', '감정 변별(4) (기쁨, 슬픔, 놀람, 화남)', '책에서 기능, 특징, 범주 중 2가지를 포함한 질문을 듣고 변별(25)', '4쌍의 형용사(크다-작다, 많다-적다, 깨끗하다-더럽다, 길다-짧다)를 변별(16)', '부정의 표현이 포함된 질문을 듣고 아이템을 변별(예: 00이 아닌 것은 뭐지?)(10)', '장소별 기능/사람/물건으로 변별(10X3=30)', '원인-결과 변별(10X2=20)', '책이나 자연스러운 환경에서 한 가지 주제에 대해 기능, 특징, 범주 관련 질문 4가지를 번갈아가며 듣고 변별(20)']}, 'directions': {'label': '6 지시따르기', 'sub': '지시따르기', 'items': ['소리가 나는 쪽으로 돌아봄', '적절한 맥락에서 안돼, 뜨거워, 잠깐과 같은 지시에 반응함', '선생님의 신호에 반응함', '호명에 눈맞춤함', '사물 단서가 있는 상황에서 지시 따르기(10)', '동작 이름을 듣고 지시를 따름(2)', '동작 이름을 듣고 지시를 따름(4)', '동작 이름을 듣고 지시를 따름(6)', '동작 이름을 듣고 지시를 따름(10)', '동작 이름을 듣고 지시를 따르거나 신체 부위를 터치함(20)', '놀이영역에서 변별하는 물건을 가져옴(10)', '놀이영역에서 동물소리, 환경음에 대해 듣고 물건을 가져옴(10)', '사물없이 동작을 시연함(10)', '2단어 지시를 따름(30)', '놀이영역에서 기능에 대해 듣고 물건을 가져옴(10)', '놀이영역에서 특징에 대해 듣고 물건을 가져옴(10)', '놀이영역에서 범주에 대해 듣고 물건을 가져옴(5)', '지시를 듣고 3명의 사람에게 감(3)', '여러 가지 사물과 동사를 섞어 2단어 지시에 따름(15)', '지시를 듣고 3개의 장소에 감', '사물을 제자리에 갖다놓음(10)', '사물을 특정한 장소에 갖다놓음(5가지 장소)', '특정 사람에게 특정 사물 갖다줌(10)', '특정 사람에게 특정 행동을 함(10)', '특정 장소에 가서 특정한 아이템을 가져옴(5가지 장소)', '2단계 동작 지시를 따름(10)', '위치가 포함된 지시를 따름(8)', '감정을 듣고 표정을 보여줌(4)', '4쌍의 부사(빨리-천천히, 높게-낮게, 크게-작게, 멀리-가까이)를 포함하여 지시를 따름(8)', '교실에서 3가지 사물을 듣고 모두 가져옴(10)', '사물을 가지고 익숙한 3단계 동작 지시를 따름(10)']}, 'requesting': {'label': '7 요구하기', 'sub': '요구하기', 'items': ['강화제에 손을 뻗음', '눈맞춤으로 요구', '성인을 잡아당김', '포인팅이나 주세요 손을 함', '2가지 선택지 중 원하는 것 포인팅', '어떤 음성이든 음성으로 맨드', '고개를 끄덕이거나 저음(동의,거절)', '원하는 것이 있을 때 성인의 신체를 두드림', '자발적인 음성 맨드(4)', '자발적인 음성 맨드(6)', '자발적인 음성 맨드(10)', '타인에게 행동 맨드(5)', '자발적인 음성 맨드(20)', '도움, 거절, 반복의 맨드(도와줘, 싫어, 또 해)', '사물의 짝 맨드 (물감-붓, 스케치북-색연필 등) (5X2=10)', '2단어로 맨드', '네/아니 맨드', '허락 구하기 맨드(00해도 돼요?)', '몰라요 표현', '언어로 A, B 중 선택', '정중한 거절과 중단 맨드', '형용사, 전치사, 부사를 포함하는 맨드(10)', '무엇이 포함된 질문 맨드(3)', '누구가 포함된 질문 맨드(3)', '어디가 포함된 질문 맨드(3)', '언제가 포함된 질문 맨드(3)', '어떻게가 포함된 질문 맨드(3)', '왜가 포함된 질문 맨드(3)', '어떻게가 포함된 질문에 대해 방법에 대한 지시나 교수(5)', '차례나 기회에 대한 맨드', '타인에게 대화 참여, 주의끌기 맨드(3)']}, 'labeling': {'label': '8 명명하기', 'sub': '명명하기', 'items': ['타인의 관심을 얻기 위해 제스쳐를 보여줌(포인팅, 손뻗기 등)', '타인의 관심을 얻기 위해 제스쳐와 음성을 동시에 사용함', '에코익으로 택트(2)', '에코익으로 택트(4)', '친숙한 사물 택트(2)', '친숙한 사물 택트(4)', '자발적 택트(6)', '자발적 택트(8)', "자연스러운 상황에서 습득한 택트에 대해 '이거 뭐야?'에 대답함", '자발적 택트(10)', '동작 택트(10)', '자발적 택트(20)', '자발적 택트(30)', '자발적 택트(40)', '자발적 택트(50)', '색깔, 모양 택트(10)', '동작 택트(20)', '장소 택트(10)', '2단어 택트(30)', '3단어 이상 택트(장소포함)(20)', '자발적 택트(200): 아이템, 동작, 색깔, 모양, 날씨, 직업 등 포함', '범주 택트(7)', '위치 택트(8) (위, 아래, 안, 밖, 앞, 뒤, 옆, 사이)', '감각 택트(10)', '같다/다르다 택트', '표정 보고 감정 택트(4)', '신체 부위의 기능 택트(6)', '형용사(4쌍)와 부사(4쌍) 택트(16)', '잘못된, 이상한, 빠진 부분 택트(20)', '한 장면을 보고 2-3문장으로 택트(20)', '접속사를 포함하여 2-3문장 이상으로 택트(10)', '자신의 과거, 미래의 사건을 설명하기(2-3문장)(10)']}, 'intraverbal': {'label': '9 인트라버벌', 'sub': '인트라버벌', 'items': ['활동 중 이어말하기(2) (예: 준비? 시작, 하나, 둘? 셋)', '동물소리, 환경음 이어말하기 인트라버벌(10) (예: 강아지는? 멍멍)', '동물소리, 환경음을 듣고 무엇인지 대답(10) (예: 멍멍? 강아지)', '동작 이어말하기(10)', '2단어 이상으로 노래이어부르기(5)', '동작 이어말하기 인트라버벌(25)', '이름/나이/유치원을 묻는 질문에 대답(3)', '무엇이 포함된 질문에 대답(예: 00으로 뭐해?, 00하는건 뭐야?)(양방향/각각20/총40)', '무엇이 포함된 질문에 대답(일반상식)(20)', '무엇이 포함된 질문에 대답(개인경험)(20)', '무엇이 포함된 질문에 대답(장소의 기능)(10)', '무엇이 포함된 질문에 대답(장소별 사물)(10)', '무엇이 포함된 질문에 대답(범주를 듣고 아이템말하기)(10)', '무엇이 포함된 질문에 대답(아이템 듣고 범주 말하기)(10)', '무엇이 포함된 질문에 대답(직업의 기능)(10)', '2가지 예시 중 선택하여 대답(20)', '네, 아니오로 질문에 대답(20)', '아이템에 대해 2가지 특징 말하기/2가지 특징을 듣고 아이템 말하기(20X2=40)', '실제 생활 아이템에 대해 3가지 특징 말하기(20)', '누구가 포함된 질문에 대답(직업의 기능/장소)(10X2=20)', '누구가 포함된 질문에 대답(책이나 사진)(20)', '어디가 포함된 질문에 대답(장소의 기능)(10)', '어디가 포함된 질문에 대답(장소별 사물)(10)', '어디가 포함된 질문에 대답(책이나 사진)(20)', '무엇, 누구, 어디에 대한 정보가 모두 포함된 책이나 사진, 실제 상황에서 3가지 이상 질문에 대답(10가지 장면)', '인트라버벌 코멘트(20)', '순서에 대한 질문에 대답(다음에/전에) (20)', '언제에 대한 질문에 대답(20) (밤/낮/아침/점심/저녁/-할때/00시/00시간)', '원인과 결과에 대한 질문에 대답(왜/어떻게) (10X2=20)', '책이나 자연스러운 환경에서 한 가지 주제에 대해 관련 질문 4가지를 번갈아가며 듣고 대답하기(20)', '이야기, 사건, 영상에 관해 듣고 설명하기(2-3문장)(20)']}}

def seed_program_master():
    if ProgramArea.query.count() == 0:
        for a_order, (key, area) in enumerate(DEFAULT_PROGRAMS.items(), start=1):
            db.session.add(ProgramArea(area_key=key, label=area["label"], sub=area["sub"], sort_order=a_order, active=True))
            for idx, name in enumerate(area["items"]):
                db.session.add(ProgramItem(area_key=key, item_index=idx, name=name, sort_order=idx, active=True))
        db.session.commit()

def initialize_database():
    db.create_all()
    seed_program_master()
    admin_username = os.environ.get("ADMIN_USERNAME", "na102502")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    admin = User.query.filter_by(username=admin_username).first()
    if not admin and admin_password:
        admin = User(username=admin_username, name="관리자", role="admin", active=True)
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()

def get_programs(include_inactive=False):
    q = ProgramArea.query.order_by(ProgramArea.sort_order, ProgramArea.id)
    if not include_inactive:
        q = q.filter_by(active=True)
    result = {}
    for area in q.all():
        iq = ProgramItem.query.filter_by(area_key=area.area_key)
        if not include_inactive:
            iq = iq.filter_by(active=True)
        items = iq.order_by(ProgramItem.sort_order, ProgramItem.item_index).all()
        result[area.area_key] = {
            "label": area.label, "sub": area.sub,
            "items": [{"item_index":x.item_index, "name":x.name, "active":x.active} for x in items]
        }
    return result

def get_program_item(area_key, item_index):
    return ProgramItem.query.filter_by(area_key=area_key, item_index=item_index, active=True).first()


def get_area_performance(child_id, area_key):
    """영역 내 기록된 각 세부항목의 초기/최근 정반응률 평균."""
    items = ProgramItem.query.filter_by(area_key=area_key, active=True).all()
    initial_rates = []
    latest_rates = []
    for item in items:
        recs = (SessionRecord.query
                .filter_by(child_id=child_id, area_key=area_key, item_index=item.item_index)
                .order_by(SessionRecord.created_at, SessionRecord.session_no)
                .all())
        recs = [r for r in recs if r.trials]
        if recs:
            initial_rates.append(recs[0].trials.count("+") * 10)
            latest_rates.append(recs[-1].trials.count("+") * 10)
    if not latest_rates:
        return {"initial": None, "latest": None, "change": None, "recorded_items": 0}
    initial = round(sum(initial_rates) / len(initial_rates))
    latest = round(sum(latest_rates) / len(latest_rates))
    return {
        "initial": initial,
        "latest": latest,
        "change": latest - initial,
        "recorded_items": len(latest_rates)
    }

def get_child_area_chart(child_id):
    rows = []
    for key, area in get_programs().items():
        perf = get_area_performance(child_id, key)
        rows.append({
            "key": key,
            "label": area["label"],
            "initial": perf["initial"],
            "latest": perf["latest"],
            "change": perf["change"],
            "recorded_items": perf["recorded_items"]
        })
    return rows

@login_manager.user_loader
def load_user(user_id): return db.session.get(User, int(user_id))

def can_access_child(child):
    return current_user.role == "admin" or child.therapist_id == current_user.id

@app.route("/", methods=["GET","POST"])
def login():
    if current_user.is_authenticated: return redirect(url_for("children"))
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and user.active and user.check_password(request.form["password"]):
            login_user(user); return redirect(url_for("children"))
        flash("아이디 또는 비밀번호를 확인해주세요.")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user(); return redirect(url_for("login"))

@app.route("/children")
@login_required
def children():
    rows = Child.query.order_by(Child.name).all() if current_user.role=="admin" else Child.query.filter_by(therapist_id=current_user.id).order_by(Child.name).all()
    return render_template("children.html", children=rows)

@app.route("/children/new", methods=["GET","POST"])
@login_required
def child_new():
    if current_user.role != "admin": abort(403)
    therapists = User.query.filter_by(role="therapist", active=True).all()
    if request.method == "POST":
        c=Child(name=request.form["name"], birth_date=request.form.get("birth_date"), start_date=request.form.get("start_date"),
                guardian_phone=request.form.get("guardian_phone"), note=request.form.get("note"),
                therapist_id=int(request.form["therapist_id"]) if request.form.get("therapist_id") else None)
        db.session.add(c); db.session.commit(); return redirect(url_for("children"))
    return render_template("child_form.html", therapists=therapists)

@app.route("/children/<int:child_id>")
@login_required
def child_detail(child_id):
    c=Child.query.get_or_404(child_id)
    if not can_access_child(c): abort(403)
    chart_rows = get_child_area_chart(child_id)
    all_states = ProgramState.query.filter_by(
        child_id=child_id
    ).all()

    item_status_map = {
        (s.area_key, s.item_index): s.status
        for s in all_states
    }
    return render_template(
    "child_detail.html",
    child=c,
    programs=get_programs(),
    chart_rows=chart_rows,
    item_status_map=item_status_map
)

@app.route("/children/<int:child_id>/program/<area_key>/<int:item_index>", methods=["GET","POST"])
@login_required
def program(child_id, area_key, item_index):
    c=Child.query.get_or_404(child_id)
    if not can_access_child(c): abort(403)
    item_obj=get_program_item(area_key,item_index)
    area_obj=ProgramArea.query.filter_by(area_key=area_key,active=True).first()
    if not item_obj or not area_obj: abort(404)

    state=ProgramState.query.filter_by(child_id=child_id,area_key=area_key,item_index=item_index).first()
    if not state:
        state=ProgramState(child_id=child_id,area_key=area_key,item_index=item_index,status="미시작")
        db.session.add(state); db.session.commit()

    if request.method=="POST":
        action=request.form.get("action")
        if action=="status":
            state.status=request.form["status"]; db.session.commit()
        elif action=="save_session":
            session_no=int(request.form["session_no"]); trials=request.form.get("trials","")[:10]
            rec=SessionRecord.query.filter_by(child_id=child_id,area_key=area_key,item_index=item_index,session_no=session_no).first()
            if not rec:
                rec=SessionRecord(child_id=child_id,area_key=area_key,item_index=item_index,session_no=session_no,
                    record_date=request.form.get("record_date") or datetime.today().strftime("%Y-%m-%d"),therapist_id=current_user.id)
                db.session.add(rec)
            rec.trials=trials; rec.record_date=request.form.get("record_date") or rec.record_date
            db.session.commit()
        return redirect(url_for("program",child_id=child_id,area_key=area_key,item_index=item_index))

    records=SessionRecord.query.filter_by(child_id=child_id,area_key=area_key,item_index=item_index).order_by(SessionRecord.session_no).all()
    stats=[]
    for r in records:
        plus=r.trials.count("+"); prompt=r.trials.count("P"); minus=r.trials.count("-")
        stats.append({"session":r.session_no,"date":r.record_date,"plus":plus,"prompt":prompt,"minus":minus,
                      "plus_rate":plus*10,"prompt_rate":prompt*10,"minus_rate":minus*10})
    area={"label":area_obj.label,"sub":area_obj.sub,"items":get_programs().get(area_key,{}).get("items",[])}

    all_states = ProgramState.query.filter_by(
        child_id=child_id,
        area_key=area_key
    ).all()

    item_status_map = {
        s.item_index: s.status
        for s in all_states
    }

    return render_template(
        "program.html",
        child=c,
        area_key=area_key,
        item_index=item_index,
        area=area,
        item=item_obj.name,
        programs=get_programs(),
        state=state,
        records=records,
        stats=stats,
        chart_stats=stats,
        item_status_map=item_status_map
    )

@app.route("/children/<int:child_id>/report")
@login_required
def report(child_id):
    c=Child.query.get_or_404(child_id)
    if not can_access_child(c): abort(403)
    rows=get_child_area_chart(child_id)
    valid=[r for r in rows if r["latest"] is not None]

    if valid:
        overall_initial=round(sum(r["initial"] for r in valid)/len(valid))
        overall_latest=round(sum(r["latest"] for r in valid)/len(valid))
        overall_change=overall_latest-overall_initial
        improved=[r for r in valid if r["change"] is not None]
        best=max(improved,key=lambda x:x["change"]) if improved else None
        lowest=min(valid,key=lambda x:x["latest"])
        summary=(
            f"기록된 영역의 평균 정반응률은 초기 {overall_initial}%에서 최근 {overall_latest}%로 "
            f"{abs(overall_change)}%p {'증가' if overall_change >= 0 else '감소'}하였습니다. "
        )
        if best and best["change"] > 0:
            summary += f"가장 큰 향상은 {best['label']} 영역에서 확인되었습니다(+{best['change']}%p). "
        summary += f"현재 상대적으로 낮은 수행은 {lowest['label']} 영역({lowest['latest']}%)에서 확인되어 지속적인 관찰이 필요합니다. "
        summary += "본 결과는 사이트에 입력된 +/P/- 수행자료를 이용한 개별 아동 내 경과 비교이며 표준화 검사나 또래 규준을 의미하지 않습니다."
    else:
        overall_initial=overall_latest=overall_change=None
        summary="아직 그래프와 비교 해설을 생성할 만큼 저장된 회기 기록이 없습니다."

    return render_template(
        "report.html", child=c, rows=rows, summary=summary,
        overall_initial=overall_initial, overall_latest=overall_latest, overall_change=overall_change
    )

@app.route("/admin/users",methods=["GET","POST"])
@login_required
def admin_users():
    if current_user.role!="admin": abort(403)
    if request.method=="POST":
        username=request.form["username"].strip()
        if User.query.filter_by(username=username).first(): flash("이미 사용 중인 아이디입니다.")
        else:
            u=User(username=username,name=request.form["name"].strip(),role=request.form.get("role","therapist"),active=True)
            u.set_password(request.form["password"]); db.session.add(u); db.session.commit(); flash("계정을 생성했습니다.")
    return render_template("users.html",users=User.query.order_by(User.role,User.name).all())

@app.route("/admin/users/<int:user_id>/password",methods=["POST"])
@login_required
def admin_user_password(user_id):
    if current_user.role!="admin": abort(403)
    u=User.query.get_or_404(user_id); u.set_password(request.form["password"]); db.session.commit()
    flash("비밀번호를 변경했습니다."); return redirect(url_for("admin_users"))

@app.route("/admin/users/<int:user_id>/toggle",methods=["POST"])
@login_required
def admin_user_toggle(user_id):
    if current_user.role!="admin": abort(403)
    u=User.query.get_or_404(user_id)
    if u.username=="na102502": flash("기본 관리자 계정은 비활성화할 수 없습니다.")
    else: u.active=not u.active; db.session.commit()
    return redirect(url_for("admin_users"))

# ---------- 관리자 프로그램 관리 ----------
@app.route("/admin/programs",methods=["GET","POST"])
@login_required
def admin_programs():
    if current_user.role!="admin": abort(403)
    if request.method=="POST":
        key=request.form["area_key"].strip()
        if not key or ProgramArea.query.filter_by(area_key=key).first():
            flash("영역 key가 비어있거나 이미 존재합니다.")
        else:
            max_order=db.session.query(db.func.max(ProgramArea.sort_order)).scalar() or 0
            db.session.add(ProgramArea(area_key=key,label=request.form["label"].strip(),sub=request.form.get("sub","").strip(),sort_order=max_order+1,active=True))
            db.session.commit(); flash("영역을 추가했습니다.")
        return redirect(url_for("admin_programs"))
    areas=ProgramArea.query.order_by(ProgramArea.sort_order,ProgramArea.id).all()
    return render_template("admin_programs.html",areas=areas)

@app.route("/admin/programs/<int:area_id>",methods=["GET","POST"])
@login_required
def admin_program_area(area_id):
    if current_user.role!="admin": abort(403)
    area=ProgramArea.query.get_or_404(area_id)
    if request.method=="POST":
        action=request.form.get("action")
        if action=="area_edit":
            area.label=request.form["label"].strip(); area.sub=request.form.get("sub","").strip(); db.session.commit()
        elif action=="add_item":
            max_index=db.session.query(db.func.max(ProgramItem.item_index)).filter_by(area_key=area.area_key).scalar()
            max_order=db.session.query(db.func.max(ProgramItem.sort_order)).filter_by(area_key=area.area_key).scalar()
            new_index=(max_index+1) if max_index is not None else 0
            new_order=(max_order+1) if max_order is not None else 0
            db.session.add(ProgramItem(area_key=area.area_key,item_index=new_index,name=request.form["name"].strip(),sort_order=new_order,active=True))
            db.session.commit()
        return redirect(url_for("admin_program_area",area_id=area.id))
    items=ProgramItem.query.filter_by(area_key=area.area_key).order_by(ProgramItem.sort_order,ProgramItem.item_index).all()
    return render_template("admin_program_area.html",area=area,items=items)

@app.route("/admin/program-item/<int:item_id>/edit",methods=["POST"])
@login_required
def admin_program_item_edit(item_id):
    if current_user.role!="admin": abort(403)
    item=ProgramItem.query.get_or_404(item_id); item.name=request.form["name"].strip(); db.session.commit()
    area=ProgramArea.query.filter_by(area_key=item.area_key).first()
    return redirect(url_for("admin_program_area",area_id=area.id))

@app.route("/admin/program-item/<int:item_id>/toggle",methods=["POST"])
@login_required
def admin_program_item_toggle(item_id):
    if current_user.role!="admin": abort(403)
    item=ProgramItem.query.get_or_404(item_id); item.active=not item.active; db.session.commit()
    area=ProgramArea.query.filter_by(area_key=item.area_key).first()
    return redirect(url_for("admin_program_area",area_id=area.id))

@app.route("/admin/program-item/<int:item_id>/move/<direction>",methods=["POST"])
@login_required
def admin_program_item_move(item_id,direction):
    if current_user.role!="admin": abort(403)
    item=ProgramItem.query.get_or_404(item_id)
    items=ProgramItem.query.filter_by(area_key=item.area_key).order_by(ProgramItem.sort_order,ProgramItem.item_index).all()
    pos=next((i for i,x in enumerate(items) if x.id==item.id),None)
    target=None
    if direction=="up" and pos is not None and pos>0: target=items[pos-1]
    if direction=="down" and pos is not None and pos<len(items)-1: target=items[pos+1]
    if target:
        item.sort_order,target.sort_order=target.sort_order,item.sort_order; db.session.commit()
    area=ProgramArea.query.filter_by(area_key=item.area_key).first()
    return redirect(url_for("admin_program_area",area_id=area.id))

@app.route("/admin/program-area/<int:area_id>/toggle",methods=["POST"])
@login_required
def admin_program_area_toggle(area_id):
    if current_user.role!="admin": abort(403)
    area=ProgramArea.query.get_or_404(area_id); area.active=not area.active; db.session.commit()
    return redirect(url_for("admin_programs"))

@app.cli.command("init-db")
def init_db():
    initialize_database(); print("DB initialized.")

with app.app_context():
    initialize_database()

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)),debug=False)
