from werkzeug.security import generate_password_hash
import psycopg2
from connect import get_db_connection





def setup_admin(full_name, username, password):
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    conn = get_db_connection()
    
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id SERIAL PRIMARY KEY,
                full_name VARCHAR(255) NOT NULL,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        try:
            cur.execute("""
                INSERT INTO admins (full_name, username, email, password) 
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (username) DO NOTHING;
            """, (full_name, username, 'admin@example.com', hashed_password))
            conn.commit()
            print("Admin account created successfully.")
        except psycopg2.Error as e:
            print(f"Database error: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    # Set up the initial admin account
    setup_admin('Admin Name', 'admin', 'admin1234abcd')


