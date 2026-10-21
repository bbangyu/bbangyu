import os
import json
from datetime import datetime

LOCKER_COUNT = 30  # 전체 락커 수 (팀과 합의 후 변경)
TIME_FORMAT = "%y/%m/%d %H:%M:%S"
YES = ("y", "yes", "예", "네")


class ExtraServiceCRUD:
    '''
    부가 서비스(락커, 운동복) 관리.
    회원별 폴더 data/members/<user_id>/extra_service.json 에 저장한다.
    락커 사용 현황은 '현재 등록된 회원'들의 파일을 읽어서 계산한다.
    '''

    def __init__(self, member_dir, member_crud):
        self.member_dir = member_dir      # 예: data/members
        self.member_crud = member_crud    # TrainerCRUD 객체 (.members 를 항상 최신으로 참조)

    # ---------- 도우미 ----------
    def get_folder(self, user_id):
        return os.path.join(self.member_dir, user_id)

    def get_path(self, user_id):
        return os.path.join(self.get_folder(user_id), "extra_service.json")

    def read_data(self, user_id):
        path = self.get_path(user_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        # 파일이 없으면 빈 기본값
        return {"locker_no": None, "assign_time": None,
                "use_uniform": None, "uniform_modify_time": None}

    def write_data(self, user_id, data):
        os.makedirs(self.get_folder(user_id), exist_ok=True)  # 개인 폴더가 없으면 생성
        with open(self.get_path(user_id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def now_time(self):
        return datetime.now().strftime(TIME_FORMAT)

    def find_member(self, user_id):
        for member in self.member_crud.members:
            if member["user_id"] == user_id:
                return member
        return None

    def locker_map(self):
        '''{락커번호: (member, data)} - 현재 사용 중인 락커만'''
        used = {}
        for member in self.member_crud.members:
            data = self.read_data(member["user_id"])
            if data["locker_no"] is not None:
                used[data["locker_no"]] = (member, data)
        return used

    def input_member(self):
        user_id = input("회원 아이디를 입력하세요: ").strip()
        member = self.find_member(user_id)
        if member is None:
            print("등록되지 않은 회원입니다.")
        return member

    def input_locker_no(self, message):
        value = input(message).strip()
        if not value.isdigit():
            print("락커 번호는 숫자로 입력해주세요.")
            return None
        number = int(value)
        if number < 1 or number > LOCKER_COUNT:
            print("존재하지 않는 락커 번호입니다.")
            return None
        return number

    def uniform_text(self, use):
        if use is None:
            return "미등록"
        return "이용" if use else "미이용"

    # ---------- 1. 락커 배정 ----------
    def do_assign_locker(self):
        member = self.input_member()
        if member is None:
            return False
        data = self.read_data(member["user_id"])
        if data["locker_no"] is not None:
            print(f"{member['name']}님은 이미 {data['locker_no']}번 락커를 사용 중입니다. (변경은 '락커 변경' 메뉴)")
            return False

        locker_no = self.input_locker_no(f"배정할 락커 번호(1~{LOCKER_COUNT}): ")
        if locker_no is None:
            return False
        if locker_no in self.locker_map():
            print("이미 사용 중인 락커입니다.")
            return False

        data["locker_no"] = locker_no
        data["assign_time"] = self.now_time()
        self.write_data(member["user_id"], data)
        print(f"{member['name']}님에게 {locker_no}번 락커를 배정했습니다.")
        return True

    # ---------- 2. 락커 현황 조회 ----------
    def do_retrieve_lockers(self):
        used = self.locker_map()
        print(f"{'=======락커 배정 현황=======':^40}")
        print(f"{'번호':<6}{'상태':<8}{'회원 아이디':<14}{'이름':<10}{'배정일시'}")
        for no in range(1, LOCKER_COUNT + 1):
            if no in used:
                member, data = used[no]
                print(f"{no:<8}{'사용중':<8}{member['user_id']:<16}{member['name']:<10}{data['assign_time']}")
            else:
                print(f"{no:<8}{'비어있음':<8}")
        print(f"사용 {len(used)} / 전체 {LOCKER_COUNT} (빈 락커 {LOCKER_COUNT - len(used)})")
        return True

    # ---------- 3. 락커 변경 및 해제 ----------
    def do_change_locker(self):
        member = self.input_member()
        if member is None:
            return False
        data = self.read_data(member["user_id"])
        if data["locker_no"] is None:
            print("배정된 락커가 없습니다. 먼저 락커를 배정해주세요.")
            return False

        print(f"현재 {data['locker_no']}번 락커를 사용 중입니다.")
        new_no = self.input_locker_no("변경할 락커 번호: ")
        if new_no is None:
            return False
        if new_no == data["locker_no"]:
            print("현재 사용 중인 락커와 같은 번호입니다.")
            return False
        if new_no in self.locker_map():
            print("이미 사용 중인 락커입니다.")
            return False

        old_no = data["locker_no"]
        data["locker_no"] = new_no
        data["assign_time"] = self.now_time()
        self.write_data(member["user_id"], data)
        print(f"{old_no}번 -> {new_no}번 락커로 변경했습니다.")
        return True

    def do_release_locker(self):
        member = self.input_member()
        if member is None:
            return False
        data = self.read_data(member["user_id"])
        if data["locker_no"] is None:
            print("배정된 락커가 없습니다.")
            return False

        check = input(f"{data['locker_no']}번 락커 사용을 해제하시겠습니까?(Y/N): ").strip().lower()
        if check not in YES:
            print("이전으로 돌아갑니다.")
            return False

        released = data["locker_no"]
        data["locker_no"] = None
        data["assign_time"] = None
        self.write_data(member["user_id"], data)
        print(f"{released}번 락커를 해제했습니다. 다시 배정할 수 있습니다.")
        return True

    # ---------- 4. 운동복 이용 여부 등록 ----------
    def do_register_uniform(self):
        member = self.input_member()
        if member is None:
            return False
        data = self.read_data(member["user_id"])
        print(f"{member['name']}님의 현재 운동복 상태: {self.uniform_text(data['use_uniform'])}")

        answer = input("운동복을 이용하시나요?(Y/N): ").strip().lower()
        if answer in YES:
            use = True
        elif answer in ("n", "no", "아니오", "아니요"):
            use = False
        else:
            print("Y 또는 N 으로 입력해주세요.")
            return False

        data["use_uniform"] = use
        data["uniform_modify_time"] = self.now_time()
        self.write_data(member["user_id"], data)
        print(f"{member['name']}님 운동복 {self.uniform_text(use)}으로 등록했습니다.")
        return True

    # ---------- 5. 운동복 이용 현황 조회 ----------
    def do_retrieve_uniform_all(self):
        members = self.member_crud.members
        if not members:
            print("등록된 회원이 없습니다.")
            return False
        print(f"{'=======운동복 이용 현황=======':^40}")
        print(f"{'회원 아이디':<14}{'이름':<10}{'운동복'}")
        use_count = 0
        for member in members:
            use = self.read_data(member["user_id"])["use_uniform"]
            if use:
                use_count += 1
            print(f"{member['user_id']:<16}{member['name']:<10}{self.uniform_text(use)}")
        print(f"이용 {use_count}명 / 전체 {len(members)}명")
        return True

    def do_retrieve_uniform_one(self):
        member = self.input_member()
        if member is None:
            return False
        data = self.read_data(member["user_id"])
        if data["use_uniform"] is None:
            print(f"{member['name']}님은 운동복 이용 여부가 등록되지 않았습니다.")
        else:
            print(f"{member['name']}님 운동복: {self.uniform_text(data['use_uniform'])} "
                  f"(최종 수정 {data['uniform_modify_time']})")
        return True

    # ---------- 회원 삭제 연동 ----------
    def remove_member_data(self, user_id):
        '''회원 삭제 시 호출: 부가 서비스 정보를 빈 값으로 초기화 (개인 폴더의 다른 파일은 건드리지 않음)'''
        if os.path.exists(self.get_path(user_id)):
            empty = {"locker_no": None, "assign_time": None,
                     "use_uniform": None, "uniform_modify_time": None}
            self.write_data(user_id, empty)


def extra_interface(extra):
    while True:
        print(
            "\n=======부가 서비스 관리=======\n"
            "1. 락커 배정\n"
            "2. 락커 배정 현황 조회\n"
            "3. 락커 변경\n"
            "4. 락커 해제\n"
            "5. 운동복 이용 여부 등록\n"
            "6. 운동복 이용 현황 조회\n"
            "7. 이전으로\n"
            "=============================="
        )
        select_num = input("번호를 입력하세요: ").strip()
        print(" ")

        if select_num == "1":
            extra.do_assign_locker()
        elif select_num == "2":
            extra.do_retrieve_lockers()
        elif select_num == "3":
            extra.do_change_locker()
        elif select_num == "4":
            extra.do_release_locker()
        elif select_num == "5":
            extra.do_register_uniform()
        elif select_num == "6":
            print("1. 전체 회원 조회\n2. 특정 회원 조회")
            sub = input("번호를 입력하세요: ").strip()
            if sub == "1":
                extra.do_retrieve_uniform_all()
            elif sub == "2":
                extra.do_retrieve_uniform_one()
            else:
                print("잘못된 접근입니다.")
        elif select_num == "7":
            print("이전 화면으로 돌아갑니다.")
            return
        else:
            print("잘못된 접근입니다.\n")
