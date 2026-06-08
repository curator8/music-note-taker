INSERT INTO auth.users (

    username,
    email,
    password_hash,
    first_name,
    last_name,
    is_active,
    email_verified,
    failed_login_attempts,
    last_login_at,
    password_changed_at,
    deleted_at

)
VALUES

(
    'joel_dev',
    'joel@email.com',
    '$2b$12$hash_1',
    'Joel',
    'Montano',
    TRUE,
    TRUE,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    NULL
),

(
    'katie_runner',
    'katie@email.com',
    '$2b$12$hash_2',
    'Katie',
    'Warren',
    TRUE,
    TRUE,
    1,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    NULL
),

(
    'analytics_mike',
    'mike@email.com',
    '$2b$12$hash_3',
    'Michael',
    'Scott',
    TRUE,
    FALSE,
    0,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    NULL
),

(
    'inactive_sarah',
    'sarah@email.com',
    '$2b$12$hash_4',
    'Sarah',
    'Johnson',
    FALSE,
    TRUE,
    3,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    NULL
),

(
    'soft_deleted_user',
    'deleted@email.com',
    '$2b$12$hash_5',
    'Deleted',
    'User',
    FALSE,
    FALSE,
    5,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);


--  inserts data into videos table
INSERT INTO auth.videos (
    user_id,
    title,
    file_path,
    description
)
VALUES
(
    1,
    'Music Lesson Video 1',
    '/video/IMG_5198.mp4',
    'Practice recording description not available yet.'
),
(
    1,
    'Music Lesson Video 2',
    '/video/IMG_5199.mp4',
    'Practice recording description not available yet.'
);
