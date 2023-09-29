import streamlit as st
import pandas as pd
from fuzzywuzzy import fuzz
import requests
import io

@st.cache_data
def load_data(url):
    response = requests.get(url)
    data = io.StringIO(response.text)
    df = pd.read_csv(data)
    df['dba'] = df['dba'].astype(str)
    df['inspection_date'] = pd.to_datetime(df['inspection_date'])
    return df.sort_values(by='inspection_date', ascending=False)

class Matcher:
    def __init__(self, df):
        self.df = df

    def find_best_match(self, user_input):
        best_match_row, best_match_score = None, 0
        for index, row in self.df.iterrows():
            row_values = ' '.join(row.astype(str).values)
            match_score = fuzz.partial_ratio(user_input.lower(), row_values.lower())
            if match_score > best_match_score:
                best_match_score, best_match_row = match_score, row
        return best_match_row

class GradeCalculator:
    @staticmethod
    def calculate(score):
        if score <= 13:
            return "A"
        elif 14 <= score <= 27:
            return "B"
        else:
            return "C"

class DisplayHandler:
    def __init__(self, best_match_row, df):
        self.best_match_row = best_match_row
        self.df = df

    def display_overview(self):
        overview_info = self.best_match_row[['dba', 'score', 'boro', 'street', 'zipcode', 'inspection_date', 'cuisine_description']]
        overview_info['inspection_date'] = overview_info['inspection_date'].strftime('%Y-%m-%d')
        overview_info['street'] = overview_info['street'].lower()
        overview_info['score'] = int(overview_info['score'])
        grade = "N/A" if pd.isnull(overview_info['score']) else GradeCalculator.calculate(int(overview_info['score']))

        overview_info_df = pd.DataFrame({'Attribute': ['grade'] + list(overview_info.index),
                                         'Value': [grade] + list(overview_info.values)})

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Overview Table:")
            st.table(overview_info_df)
        return col2

    def display_images(self, col):
        self._check_and_display_images(self.best_match_row, self.df, col)

    def display_violations(self):
        camis_value, inspection_date = self.best_match_row['camis'], self.best_match_row['inspection_date']
        matching_rows = self.df[(self.df['camis'] == camis_value) & (self.df['inspection_date'] == inspection_date)]
        critical_violations = matching_rows[matching_rows['critical_flag'] == 'Critical']['violation_description']
        noncritical_violations = matching_rows[matching_rows['critical_flag'] == 'Not Critical']['violation_description']

        if not critical_violations.empty:
            st.write("**Critical Violations:**")
            for violation in critical_violations:
                st.write(violation)

        if not noncritical_violations.empty:
            st.write("**Non-Critical Violations:**")
            for violation in noncritical_violations:
                st.write(violation)

    @staticmethod
    def _check_and_display_images(best_match_row, df, col):
        camis_value, inspection_date = best_match_row['camis'], best_match_row['inspection_date']
        matching_rows = df[(df['camis'] == camis_value) & (df['inspection_date'] == inspection_date)]
        violation_descriptions = matching_rows['violation_description'].str.lower()

        if any("evidence of rats" in description for description in violation_descriptions):
            col.image('https://media.istockphoto.com/id/165655302/vector/rat-cartoon-thumbs-up.jpg?s=612x612&w=0&k=20&c=cHqlmywrwiSuO96Vl7gqGMoULsg2ETwnPqU91-FIg14=', caption='Evidence of Rats')
        if any("evidence of mice" in description for description in violation_descriptions):
            col.image('https://www.freethink.com/wp-content/uploads/2023/03/mice-with-two-dads-thumb.jpg?w=640', caption='Evidence of Mice')

def main():
    st.title("NYC Restaurant Inspection Portal")

    st.sidebar.markdown("## Search")
    user_input = st.sidebar.text_input("Enter a restaurant name and / or other details:")
    search_button = st.sidebar.button("Search")

    if search_button:
        if user_input:
            with st.spinner("Fetching data..."):
                df = load_data('https://raw.githubusercontent.com/ssaurbier/restaurants_inspections/main/health_data.csv')
            matcher = Matcher(df)  
            best_match_row = matcher.find_best_match(user_input)
            if best_match_row is not None:
                display_handler = DisplayHandler(best_match_row, df)
                col = display_handler.display_overview()
                display_handler.display_images(col)
                display_handler.display_violations()
            else:
                st.error("No matching rows found.")
        else:
            st.warning("Please enter a search query.")

if __name__ == "__main__":
    main()
