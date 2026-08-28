환자 관리 · 진료기록 API 설계
공통 규칙
Base URL: /api/v1
모든 API는 JWT Access Token 인증이 필요하다.
요청 헤더:
Authorization: Bearer <access_token>
환자 등록과 진료기록 등록은 의료 부서(MEDICAL) 사용자만 가능하다고 가정한다.
환자 조회·수정·삭제와 진료기록 조회는 모든 로그인 사용자가 가능하다.
상태 코드	의미
200	조회 또는 수정 성공
201	등록 성공
204	삭제 성공
401	로그인 정보 없음 또는 토큰 만료
403	권한 없음
404	환자 또는 진료기록 없음
422	요청 데이터 검증 실패


API 목록
요구사항 ID	기능	Method	URL
REQ-PTNT-001	환자 정보 등록	POST	/patients
REQ-PTNT-002	환자 목록 조회	GET	/patients
REQ-PTNT-003	환자 상세 조회	GET	/patients/{patient_id}
REQ-PTNT-004	환자 정보 수정	PATCH	/patients/{patient_id}
REQ-PTNT-005	환자 정보 삭제	DELETE	/patients/{patient_id}
REQ-MDR-001	진료기록 등록	POST	/patients/{patient_id}/medical-records
REQ-MDR-002	진료기록 목록 조회	GET	/patients/{patient_id}/medical-records
REQ-MDR-003	진료기록 상세 조회	GET	/patients/{patient_id}/medical-records/{record_id}


환자 정보 등록
POST /api/v1/patients
의료 부서 사용자가 환자 정보를 등록한다.
{
  "name": "홍길동",
  "age": 45,
  "gender": "M",
  "phone": "01012345678"
}
필드	타입	필수	설명
name	string	O	환자 이름
age	integer	O	환자 나이
gender	string	O	M 또는 F
phone	string	O	휴대폰 번호


응답: 201 Created
{
  "id": 1,
  "name": "홍길동",
  "age": 45,
  "gender": "M",
  "phone": "01012345678",
  "created_at": "2026-08-28T10:00:00"
}
환자 목록 조회
GET /api/v1/patients
환자 이름 검색, 성별·나이 범위 필터, 페이지네이션을 제공한다.
GET /api/v1/patients?keyword=홍&gender=M&min_age=30&max_age=60&page=1&size=20
파라미터	설명
keyword	환자 이름 검색어
gender	성별 필터 (M, F)
min_age	최소 나이
max_age	최대 나이
page	페이지 번호
size	페이지당 항목 수


응답: 200 OK
{
  "items": [
    {
      "id": 1,
      "name": "홍길동",
      "age": 45,
      "gender": "M",
      "phone": "01012345678",
      "created_at": "2026-08-28T10:00:00",
      "updated_at": "2026-08-28T10:00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
환자 상세 조회
GET /api/v1/patients/{patient_id}
응답: 200 OK
{
  "id": 1,
  "name": "홍길동",
  "age": 45,
  "gender": "M",
  "phone": "01012345678",
  "created_at": "2026-08-28T10:00:00",
  "updated_at": "2026-08-28T10:00:00"
}
환자 정보 수정
PATCH /api/v1/patients/{patient_id}
요구사항에 따라 이름과 연락처만 부분 수정한다.
{
  "name": "홍길순",
  "phone": "01098765432"
}
이름만 수정할 경우에는 수정할 값만 전송한다.
{
  "name": "홍길순"
}
응답: 200 OK
{
  "id": 1,
  "name": "홍길순",
  "age": 45,
  "gender": "M",
  "phone": "01098765432",
  "updated_at": "2026-08-28T11:00:00"
}
환자 정보 삭제
DELETE /api/v1/patients/{patient_id}
환자와 연결된 진료기록 및 X-Ray 이미지도 함께 삭제한다.
Patient 삭제
  └─ MedicalRecord 삭제
      └─ XrayImage 삭제
      └─ AiAnalysisResult 삭제
응답: 204 No Content
진료기록 등록
POST /api/v1/patients/{patient_id}/medical-records
진료기록과 X-Ray 이미지를 함께 등록하므로 multipart/form-data 형식을 사용한다.
필드	타입	필수	설명
chart_number	string	O	진료 차트 넘버
symptoms	string	O	진료된 증상
xray_image	file	O	촬영된 흉부 X-Ray 이미지


응답: 201 Created
{
  "id": 1,
  "patient_id": 1,
  "chart_number": "CHART-20260828-001",
  "symptoms": "기침, 발열 증상",
  "xray_image_url": "/media/xray/record-1.png",
  "created_at": "2026-08-28T12:00:00"
}
진료기록 목록 조회
GET /api/v1/patients/{patient_id}/medical-records
응답: 200 OK
{
  "items": [
    {
      "id": 1,
      "chart_number": "CHART-20260828-001",
      "symptoms_preview": "기침, 발열 증상",
      "created_at": "2026-08-28T12:00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
증상은 목록에서 최대 100자까지만 보여준다.
진료기록 상세 조회
GET /api/v1/patients/{patient_id}/medical-records/{record_id}
응답: 200 OK
{
  "id": 1,
  "patient_id": 1,
  "chart_number": "CHART-20260828-001",
  "symptoms": "기침, 발열 증상이 3일간 지속됨",
  "xray_images": [
    {
      "id": 1,
      "image_url": "/media/xray/record-1.png",
      "shooting_datetime": "2026-08-28T11:30:00"
    }
  ],
  "created_at": "2026-08-28T12:00:00"
}
성능 고려 사항
모든 환자·진료기록 API는 3초 이내 응답을 목표로 한다.
목록 조회에 페이지네이션 적용
환자 이름 검색을 위한 인덱스 고려
성별·나이 필터를 DB Query에서 처리
목록 조회에서는 X-Ray 이미지 전체를 조회하지 않음
이미지 파일 자체가 아닌 이미지 URL을 응답으로 전달
요구사항에는 진료기록 수정·삭제 기능이 없으므로, 이번 API 설계에는 진료기록 등록·조회 기능만 포함한다.