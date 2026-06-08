CREATE SCHEMA IF NOT EXISTS auth; 

DROP TABLE IF EXISTS auth.users;

CREATE TABLE auth.users (
	user_id SERIAL PRIMARY KEY,
	username VARCHAR(50) UNIQUE NOT NULL,
	email VARCHAR(255) UNIQUE NOT NULL,
	password_hash TEXT NOT NULL, 
	first_name VARCHAR(100), 
	last_name VARCHAR(100), 
	is_active BOOLEAN DEFAULT TRUE,
	email_verified BOOLEAN NOT NULL DEFAULT FALSE,
	failed_login_attempts INTEGER NOT NULL DEFAULT 0,
	last_login_at TIMESTAMP,
	password_changed_at TIMESTAMP,
	create_dt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	deleted_at TIMESTAMP 
); 

select * from auth.users 

DROP TABLE IF EXISTS auth.videos;

CREATE TABLE auth.videos (
	video_id SERIAL PRIMARY KEY,
	user_id INTEGER REFERENCES auth.users(user_id),
	title VARCHAR(255) NOT NULL,
	file_path TEXT NOT NULL,
	description TEXT,
	create_dt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

select * from auth.videos
