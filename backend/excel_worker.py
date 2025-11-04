import sys
import json
import sqlite3
import pandas as pd
import os

def main():
    if len(sys.argv) < 3:
        print(json.dumps({'error':'usage: excel_worker.py <excel_path> <db_path>'}))
        return
        
    excel_path, db_path = sys.argv[1], sys.argv[2]
    # optional override date passed as third argument
    override_date = sys.argv[3] if len(sys.argv) > 3 else None

    try:
        # Read Excel file
        df = pd.read_excel(excel_path)
        
        # Define column name mappings (common variants)
        column_mappings = {
            'reg_no': ['reg_no', 'regno', 'registration_no', 'registration number', 'reg no', 'register no'],
            'seat_no': ['seat_no', 'seatno', 'seat number', 'seat no'],
            'room': ['room', 'hall', 'room_no', 'room no', 'hall no'],
            'course_code': ['course_code', 'coursecode', 'course code', 'subject code'],
            'course_title': ['course_title', 'coursetitle', 'course title', 'subject', 'subject name'],
            'session': ['session', 'exam session', 'exam_session'],
            'date': ['date', 'exam_date', 'exam date']
        }
        
        # Function to find the actual column name in DataFrame
        def find_column(possible_names):
            for name in possible_names:
                matches = [col for col in df.columns if col.lower().strip().replace(' ', '_') == name.lower().strip().replace(' ', '_')]
                if matches:
                    return matches[0]
            return None
            
        # Map columns to standard names
        column_rename = {}
        for std_name, variants in column_mappings.items():
            found_col = find_column(variants)
            if found_col and found_col != std_name:
                column_rename[found_col] = std_name
        
        # Rename columns to standard names
        if column_rename:
            df = df.rename(columns=column_rename)
        
        required_columns = ['reg_no', 'seat_no', 'room', 'course_code', 'course_title', 'session']
        
        # Check if required columns exist (after mapping)
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(json.dumps({
                'error': f'Missing required columns: {", ".join(missing_columns)}. Expected columns are: Registration Number, Seat Number, Room/Hall, Course Code, Course Title, Session'
            }))
            return

        # Connect to database
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Ensure table exists
        cur.execute('''CREATE TABLE IF NOT EXISTS students (
            reg_no TEXT,
            seat_no TEXT,
            room TEXT, 
            course_code TEXT,
            course_title TEXT,
            date TEXT,
            session TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (reg_no, date, session)
        )''')

        # Insert data
        inserted = 0
        for _, row in df.iterrows():
            try:
                # Handle date: use override_date or Excel date, ensure proper format
                if override_date:
                    date = override_date
                elif 'date' in row and pd.notna(row['date']):
                    # Convert Excel date to DD.MM.YYYY format
                    date = pd.to_datetime(row['date']).strftime('%d.%m.%Y')
                else:
                    # No default date - leave it null in DB
                    date = None
                
                # Clean and validate data before insertion
                reg_no = str(row['reg_no']).strip()
                seat_no = str(row['seat_no']).strip() if pd.notna(row['seat_no']) else None
                room = str(row['room']).strip() if pd.notna(row['room']) else None
                course_code = str(row['course_code']).strip() if pd.notna(row['course_code']) else None
                course_title = str(row['course_title']).strip() if pd.notna(row['course_title']) else None
                session = str(row['session']).strip().upper() if pd.notna(row['session']) else None
                
                if not reg_no:  # Skip row if registration number is empty
                    continue
                    
                cur.execute('''INSERT OR REPLACE INTO students 
                    (reg_no, seat_no, room, course_code, course_title, date, session)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (reg_no, seat_no, room, course_code, course_title, date, session))
                inserted += 1
            except Exception as e:
                print(json.dumps({'error': f'Error inserting row {inserted + 1}: {str(e)}'}))
                continue

        conn.commit()
        conn.close()
        print(json.dumps({'inserted': inserted}))

    except Exception as e:
        print(json.dumps({'error': str(e)}))

if __name__ == "__main__":
    main()