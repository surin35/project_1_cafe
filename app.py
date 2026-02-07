import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

# 페이지 설정
st.set_page_config(page_title="서울시 카페 입지 분석 대시보드", layout="wide")

# 데이터 로드 함수 (캐싱 적용)
@st.cache_data
def load_data():
    base_path = r'c:\ICB6\fcicb6\project_1_cafe\data_2'
    cafe_path = os.path.join(base_path, 'cafe_data_merge.csv')
    work_path = os.path.join(base_path, 'seoul_work_data_updated.csv')
    
    # 카페 데이터 로드
    df = pd.read_csv("data_2/cafe_data_merge.csv")
    
    # 종사자 데이터 로드 및 전처리
    work_df = pd.read_csv(work_path, encoding='cp949')
    work_cols = work_df.columns.tolist()
    dong_col, worker_col = work_cols[2], work_cols[4]
    work_df_filtered = work_df[~work_df[dong_col].isin(['소계', '합계', '전체'])].copy()
    work_df_filtered[worker_col] = pd.to_numeric(work_df_filtered[worker_col], errors='coerce')
    work_df_filtered = work_df_filtered[[dong_col, worker_col]]
    work_df_filtered.columns = ['행정동명', '종사자수']
    
    return df, work_df_filtered

# 타이틀
st.title("☕ 서울시 행정동별 카페 입지 분석 대시보드")
st.markdown("서울시의 카페 분포와 직장인(종사자) 데이터를 결합하여 최적의 카페 입지를 탐색합니다.")

# 데이터 불러오기
try:
    df, worker_df = load_data()
    hjd_name_col = df.columns[-2]
    shop_name_col = df.columns[21]
    
    # 기초 전처리: 저가 브랜드 식별
    budget_brands = {'메가커피': '메가커피|메가엠지씨', '빽다방': '빽다방', '컴포즈커피': '컴포즈', '더벤티': '더벤티', '매머드커피': '매머드|메머드'}
    df['저가브랜드'] = None
    for brand, pattern in budget_brands.items():
        mask = df[shop_name_col].str.contains(pattern, case=False, na=False, regex=True)
        df.loc[mask, '저가브랜드'] = brand

    # 사이드바 필터
    st.sidebar.header("🔍 데이터 필터링")
    
    # 1. 브랜드 필터
    selected_brands = st.sidebar.multiselect("분석할 저가 브랜드 선택", options=list(budget_brands.keys()), default=list(budget_brands.keys()))
    
    # 2. 행정동별 입지 점수 계산을 위한 병합 데이터 미리 생성
    cafe_counts = df[hjd_name_col].value_counts().reset_index()
    cafe_counts.columns = ['행정동명', '카페수']
    merge_df = pd.merge(worker_df, cafe_counts, on='행정동명', how='inner')
    merge_df['입지점수'] = merge_df['종사자수'] / merge_df['카페수']
    
    # 3. 입지 점수 범위 필터
    min_score = float(merge_df['입지점수'].min())
    max_score = float(merge_df['입지점수'].max())
    score_range = st.sidebar.slider("입지 점수 범위 필터", min_score, max_score, (min_score, max_score))
    
    # 필터링 적용된 데이터
    filtered_merge = merge_df[(merge_df['입지점수'] >= score_range[0]) & (merge_df['입지점수'] <= score_range[1])]
    filtered_cafe = df[df[hjd_name_col].isin(filtered_merge['행정동명'])]

    # 탭 구성
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 개요", "🏘️ 카페 분포", "💼 종사자 분석", "📈 입지 전략", "📍 지도 보기"])

    with tab1:
        st.header("데이터 세트 요약")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("총 점포 수", f"{len(df):,}개")
        col2.metric("분석 대상 행정동", f"{len(merge_df):,}개")
        col3.metric("평균 입지 점수", f"{merge_df['입지점수'].mean():.2f}")
        col4.metric("저가 브랜드 점포", f"{df['저가브랜드'].notnull().sum():,}개")
        
        st.subheader("데이터 통계 정보 (표 1)")
        st.dataframe(merge_df.describe(), use_container_width=True)
        
        st.subheader("결측치 현황 (표 2)")
        missing_df = df.isnull().sum().reset_index()
        missing_df.columns = ['컬럼명', '결측치수']
        st.table(missing_df.sort_values(by='결측치수', ascending=False).head(10))

    with tab2:
        st.header("행정동별 카페 분포 분석")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("카페 수 상위 20개 행정동 (그래프 1)")
            fig1 = px.bar(cafe_counts.head(20), x='행정동명', y='카페수', color='카페수', color_continuous_scale='Blues')
            st.plotly_chart(fig1, use_container_width=True)
            
        with col2:
            st.subheader("저가커피 브랜드 시장 점유율 (그래프 2)")
            brand_counts = df['저가브랜드'].value_counts().reset_index()
            brand_counts.columns = ['브랜드', '점포수']
            fig2 = px.pie(brand_counts, values='점포수', names='브랜드', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig2, use_container_width=True)
            
        st.subheader("행정동별 브랜드 분포 교차표 (표 3)")
        budget_filtered = df[df['저가브랜드'].isin(selected_brands)]
        brand_ct = pd.crosstab(budget_filtered[hjd_name_col], budget_filtered['저가브랜드'], margins=True, margins_name="합계")
        st.dataframe(brand_ct.sort_values(by="합계", ascending=False).head(20), use_container_width=True)

    with tab3:
        st.header("행정동별 종사자 분석")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("종사자 수 상위 20개 행정동 (그래프 3)")
            fig3 = px.bar(worker_df.head(20), x='행정동명', y='종사자수', color='종사자수', color_continuous_scale='Reds')
            st.plotly_chart(fig3, use_container_width=True)
            
        with col2:
            st.subheader("종사자수 vs 카페수 상관관계 (그래프 4)")
            fig4 = px.scatter(merge_df, x='종사자수', y='카페수', hover_name='행정동명', size='입지점수', color='입지점수')
            st.plotly_chart(fig4, use_container_width=True)
            
        st.subheader("종사자 데이터 상세 (표 4)")
        st.dataframe(worker_df.head(50), use_container_width=True)

    with tab4:
        st.header("카페 입지 전략 인사이트")
        st.subheader("입지 점수 상위 행정동 (그래프 5)")
        st.markdown("**입지 점수 = 종사자 수 / 카페 수**. 점수가 높을수록 한 카페당 잠재 고객이 많음을 의미합니다.")
        fig5 = px.bar(filtered_merge.sort_values(by='입지점수', ascending=False).head(20), x='행정동명', y='입지점수', color='입지점수')
        st.plotly_chart(fig5, use_container_width=True)
        
        st.subheader("전략적 분석 결과 (표 5)")
        st.dataframe(filtered_merge.sort_values(by='입지점수', ascending=False).reset_index(drop=True), use_container_width=True)

    with tab5:
        st.header("지리적 데이터 시각화")
        st.markdown("카페 데이터에 포함된 좌표를 활용하여 실제 위치를 확인합니다. (데이터가 많아 샘플링 2,000개)")
        map_df = df.dropna(subset=['위도', '경도']).sample(n=min(2000, len(df)))
        st.map(map_df[['위도', '경도']])

except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")
    st.info("데이터 파일이 올바른 위치에 있는지, 인코딩이 cp949인지 확인해 주세요.")

