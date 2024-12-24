import traceback
import psycopg2


# ______________________________________________________________________________
# __________________Comment Or Uncomment For POSTGRES DATABASE SETUP_______________
# -------------------------------------------------------------------------------

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host='localhost', 
            database='window_account_db', 
            user='postgres', 
            password='postgres'
            )
        print("Successfully connected to database!")
        return conn
    except psycopg2.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    return None
get_db_connection()


def create_tables():
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            
            # Create the tables if it doesn't exist SQL COMMANDS                       
            cur.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    id SERIAL PRIMARY KEY,
                    full_name VARCHAR(255) NOT NULL,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL, -- Store encrypted password
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS staffs (
                    id SERIAL PRIMARY KEY,
                    full_name VARCHAR(255) NOT NULL,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    staff_number VARCHAR(100) UNIQUE,
                    department VARCHAR(100) NOT NULL,
                    position VARCHAR(100),
                    branch VARCHAR(100),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL, -- Store encrypted password
                    approved BOOLEAN DEFAULT FALSE, -- Admin approval status
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""ALTER TABLE staffs ALTER COLUMN staff_number DROP NOT NULL;""")           
            cur.execute("""ALTER TABLE staffs ADD COLUMN IF NOT EXISTS description VARCHAR(800);""")           
            cur.execute("""ALTER TABLE staffs ADD COLUMN IF NOT EXISTS profile_pic TEXT;""")           

            


            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tools (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL, -- Tool name, e.g., Slack, Titan, WhatsApp
                    url VARCHAR(255) NOT NULL, -- Tool base URL, e.g., https://slack.com, https://web.whatsapp.com
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""ALTER TABLE tools ADD COLUMN IF NOT EXISTS logo_url VARCHAR(255);""")           

            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS staff_tools (
                    id SERIAL PRIMARY KEY,
                    staff_id INT REFERENCES staffs(id) ON DELETE CASCADE, -- Staff reference
                    tool_id INT REFERENCES tools(id) ON DELETE CASCADE, -- Tool reference
                    custom_url VARCHAR(255), -- Optional custom URL for specific tool links
                    added_by_admin BOOLEAN DEFAULT FALSE, -- Whether tool was added by admin or staff
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            cur.execute("""
                    CREATE TABLE IF NOT EXISTS local_tools (
                        id SERIAL PRIMARY KEY,
                        staff_id INT REFERENCES staffs(id) ON DELETE CASCADE,
                        file_name VARCHAR(255) NOT NULL,
                        file_url VARCHAR(255) NOT NULL,
                        file_type VARCHAR(200) NOT NULL, -- to store the type of the file (e.g., 'image/png', 'application/pdf', etc.)
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """)
            
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS approval_requests (
                    id SERIAL PRIMARY KEY,
                    staff_id INT REFERENCES staffs(id) ON DELETE CASCADE, -- Staff reference
                    request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- When the request was made
                    approved_time TIMESTAMP, -- When the request was approved
                    approved_by INT REFERENCES admins(id) ON DELETE SET NULL -- Admin who approved the request
                );
            """)
            
            
        # -- Conversations table: stores conversation details      
            cur.execute(""" 
                CREATE TABLE IF NOT EXISTS conversations (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255),  -- Optional: name of the conversation or group
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );                        
                """)
            # cur.execute("""ALTER TABLE conversations ADD CONSTRAINT unique_conversation_name UNIQUE (name);""")
            
        # --Conversation participants table: maps staff members to conversations 
            cur.execute(""" 
                CREATE TABLE IF NOT EXISTS conversation_participants (
                    id SERIAL PRIMARY KEY,
                    conversation_id INT REFERENCES conversations(id) ON DELETE CASCADE,
                    staff_id INT REFERENCES staffs(id) ON DELETE CASCADE,
                    UNIQUE (conversation_id, staff_id)
                );                      
            """)
            
        # -- Messages table: stores individual messages
            cur.execute(""" 
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    conversation_id INT REFERENCES conversations(id) ON DELETE CASCADE,
                    sender_id INT REFERENCES staffs(id) ON DELETE CASCADE,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );                     
            """)
            
            print("Database tables created successfully")
            conn.commit()

        except psycopg2.Error as e:
            print(f"Database error: {e}")
        except Exception as e:
            traceback.print_exc()
            print(f"Error: {e}")
        finally:
            cur.close()
            conn.close()
    else:
        print("Could not open connection to the database")

# Call the function to initialize the database
create_tables()
