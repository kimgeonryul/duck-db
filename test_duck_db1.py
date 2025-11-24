

# conn = duckdb.connect(database='madang.db')
# conn.sql("create table Customer as select * from 'Customer_madang.csv'")
# conn.sql("create table Book as select * from 'Book_madang.csv'")
# conn.sql("create table Orders as select * from 'Orders_madang.csv'")
# conn.close()

import streamlit as st
import duckdb
import pandas as pd
from datetime import datetime

# ----------------- DuckDB 연결 및 쿼리 함수 정의 -----------------
DB_FILE_PATH = "madang.db" 

@st.cache_resource
def get_duckdb_connection():
    try:
        conn = duckdb.connect(database=DB_FILE_PATH, read_only=False)
        return conn
    except Exception as e:
        st.error(f"DuckDB 연결 오류: {e}")
        return None

conn = get_duckdb_connection()

def run_dml(sql):
    if conn is None:
        return False
    try:
        conn.execute(sql)
        st.cache_data.clear() 
        return True
    except Exception as e:
        st.error(f"쿼리 실행 중 오류 발생. SQL 구문을 확인하세요: {e}")
        st.code(sql, language='sql')
        return False

# 3. SELECT 쿼리 실행 및 캐시 적용 함수 (기존 코드 유지)
# ... (get_customer_data, get_Orders_data, get_book_data 함수는 그대로 유지합니다.)
@st.cache_data(ttl=60) # 1분 캐싱
def get_customer_data():
    if conn is None:
        return pd.DataFrame()
    try:
        return conn.execute("SELECT * FROM Customer ORDER BY custid").df()
    except Exception as e:
        st.error(f"테이블 조회 오류: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60) # 1분 캐싱
def get_Orders_data():
    if conn is None:
        return pd.DataFrame()
    try:
        return conn.execute("SELECT * FROM Orders ORDER BY custid").df()
    except Exception as e:
        st.error(f"테이블 조회 오류: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60) # 1분 캐싱
def get_book_data():
    if conn is None:
        return pd.DataFrame()
    try:
        return conn.execute("SELECT * FROM Book ORDER BY bookid").df()
    except Exception as e:
        st.error(f"테이블 조회 오류: {e}")
        return pd.DataFrame()


def get_next_order_id():
    """Orders 테이블에서 최대 orderid를 조회하고 1을 더한 값을 반환합니다."""
    if conn is None:
        return None
    try:
        # SQL을 사용하여 최대 orderid를 조회하고 1을 더합니다.
        result = conn.execute("SELECT COALESCE(MAX(orderid), 0) + 1 FROM Orders").fetchone()
        return result[0]
    except Exception as e:
        st.error(f"다음 OrderID 조회 오류: {e}")
        return None

# ----------------- Streamlit UI -----------------

st.title("마당DB 도서관리 앱")
st.header("12243320 김건률")

if conn:
    # --- 고객 별 주문 조회 섹션 ---
    st.header("고객 별 주문 조회")

    with st.form("select_form"):
        st.markdown("##### 고객 ID를 선택하여 해당 고객의 주문 내역을 조회하세요.")
        
        customer_df = get_customer_data()
        custid_options = customer_df['custid'].tolist()
        
        # custid_options가 비어있지 않은지 확인 (최소 하나의 고객이 있어야 함)
        if not custid_options:
            st.warning("Customer 테이블에 데이터가 없습니다. 먼저 고객을 삽입하세요.")
            selected_custid = None
        else:
            selected_custid = st.selectbox("고객 ID 선택", custid_options)
        
        submitted = st.form_submit_button("주문 내역 조회")
        
        if submitted and selected_custid is not None:
            try:
                orders_df = conn.execute(f"""
                SELECT o.orderid, o.custid, c.name, o.bookid, o.saleprice, o.orderdate FROM Orders o inner join Customer c on c.custid = o.custid WHERE o.custid = {selected_custid} ORDER BY orderid
                """).df()
                
                st.subheader(f"CustID {selected_custid} 고객의 주문 내역")
                st.dataframe(orders_df)
            except Exception as e:
                st.error(f"주문 내역 조회 오류: {e}")

    # --- 데이터 삽입 섹션 (Customer) ---
    st.header("새로운 고객 정보 삽입")
    with st.form("insert_form", clear_on_submit=True):
        st.markdown("##### 고객 정보 입력")
        
        try:
            next_custid = conn.execute("SELECT COALESCE(MAX(custid), 0) + 1 FROM Customer").fetchone()[0]
        except:
            next_custid = 0 # 오류 시 기본값
            
        new_custid = st.number_input("CustID (숫자)", min_value=1, value=next_custid, step=1)
        new_name = st.text_input("Name (이름)", "홍길동")
        new_address = st.text_input("Address (주소)", "인천광역시")
        new_phone = st.text_input("Phone (전화번호)", "010-1234-5678")
        
        submitted = st.form_submit_button("고객 정보 삽입 (INSERT)")
        
        if submitted:
            insert_sql = f"""
            INSERT INTO Customer (custid, name, address, phone) 
            VALUES ({new_custid}, '{new_name}', '{new_address}', '{new_phone}');
            """
            
            if run_dml(insert_sql):
                st.success(f"CustID {new_custid} 고객 정보가 삽입되었습니다.")

    # --- 주문 정보 삽입 섹션 (Orders) ---
    st.header("주문 정보 삽입")
    with st.form("inesrt_order_form", clear_on_submit=True):
        st.markdown("##### 주문 정보 입력")
        
        next_order_id = get_next_order_id()
        st.info(f"다음 OrderID는 **{next_order_id}**로 자동 설정됩니다.")
        
        book_df = get_book_data()
        bookid_options = book_df['bookid'].tolist()
        
        order_custid = st.number_input("CustID (숫자)", min_value=1, value=1, step=1, key="order_custid")
        
        selected_bookid = st.selectbox("도서 ID 선택", bookid_options, key="order_bookid") 
        
            
        order_saleprice = st.number_input("판매가격", min_value=0, value=10000, step=1000, key="order_saleprice")
        
        # 현재 날짜를 문자열로 포맷 (SQL에 맞게)
        order_date_str = datetime.now().strftime("'%Y-%m-%d'") 
        
        st.caption(f"주문 날짜는 현재 날짜로 자동 설정됩니다.")

        submitted = st.form_submit_button("주문 정보 삽입 (INSERT)")
        
        if submitted and next_order_id is not None:
            insert_order_sql = f"""
            INSERT INTO Orders (orderid, custid, bookid, saleprice, orderdate) 
            VALUES ({next_order_id}, {order_custid}, {selected_bookid}, {order_saleprice}, {order_date_str});
            """
            
            if run_dml(insert_order_sql):
                st.success(f"Order ID **{next_order_id}**의 주문 정보가 성공적으로 삽입되었습니다.")
        elif submitted and next_order_id is None:
            st.error("OrderID를 생성할 수 없습니다. DB 연결 상태를 확인하세요.")
    
            
    # --- 데이터 확인 섹션 (기존 코드 유지) ---
    st.header("Customer 테이블")
    customer_df = get_customer_data()
    st.dataframe(customer_df)

    st.header("Orders 테이블")
    orders_df = get_Orders_data()
    st.dataframe(orders_df)

    st.header("Book 테이블")
    book_df = get_book_data()
    st.dataframe(book_df)



    st.header("직접 SQL 쿼리 실행 (Expert Mode)")
    st.warning("⚠️ **주의**")

    with st.form("custom_query_form"):
        # 쿼리 입력 텍스트 영역
        custom_query = st.text_area(
            "실행할 SQL 쿼리를 입력하세요:", 
            "SELECT * FROM Customer LIMIT 5;", # 기본 쿼리
            height=150
        )
        execute_button = st.form_submit_button("쿼리 실행")
        
        if execute_button:
            # 쿼리의 첫 번째 키워드를 분석하여 SELECT인지 DML/DDL인지 판단합니다.
            sql_stripped = custom_query.strip()
            if not sql_stripped:
                st.error("쿼리를 입력해 주세요.")
            else:
                query_type = sql_stripped.upper().split(' ')[0]
                
                if query_type == 'SELECT':
                    # SELECT 쿼리 실행
                    try:
                        # SELECT 쿼리는 캐싱 없이 즉시 결과를 가져옵니다.
                        result_df = conn.execute(sql_stripped).df()
                        
                        st.subheader("쿼리 실행 결과")
                        st.dataframe(result_df)
                        st.success("SELECT 쿼리가 성공적으로 실행되었습니다.")
                        
                    except Exception as e:
                        st.error(f"SELECT 쿼리 실행 오류: {e}")
                        st.code(sql_stripped, language='sql')
                        
                else:
                    if run_dml(sql_stripped):
                        st.success(f"쿼리 타입({query_type})이 성공적으로 실행되었습니다. 관련 테이블을 새로고침하여 확인하세요.")
else:
    st.error("DuckDB 연결이 실패하여 앱을 사용할 수 없습니다.")