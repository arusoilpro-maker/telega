-- =====================================================
-- ПОЛНАЯ СХЕМА БАЗЫ ДАННЫХ ДЛЯ МАРКЕТПЛЕЙСА МАСТЕРОВ
-- =====================================================

CREATE DATABASE IF NOT EXISTS repair_marketplace 
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE repair_marketplace;

-- =====================================================
-- ПОЛЬЗОВАТЕЛИ И ПРОФИЛИ
-- =====================================================

CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    uuid CHAR(36) UNIQUE NOT NULL DEFAULT (UUID()),
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    middle_name VARCHAR(100),
    avatar_url TEXT,
    role ENUM('client', 'master', 'admin', 'super_admin') DEFAULT 'client',
    status ENUM('active', 'blocked', 'pending', 'deleted') DEFAULT 'pending',
    
    -- Authentication
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE,
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    two_factor_secret VARCHAR(255),
    auth_provider ENUM('local', 'telegram', 'google', 'facebook') DEFAULT 'local',
    social_id VARCHAR(255),
    
    -- Security
    last_login_ip VARCHAR(45),
    last_login_at TIMESTAMP NULL,
    login_attempts INT DEFAULT 0,
    blocked_until TIMESTAMP NULL,
    password_changed_at TIMESTAMP NULL,
    
    -- Preferences
    language VARCHAR(10) DEFAULT 'ru',
    currency VARCHAR(3) DEFAULT 'RUB',
    timezone VARCHAR(50) DEFAULT 'Europe/Moscow',
    notification_settings JSON,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    
    INDEX idx_email (email),
    INDEX idx_phone (phone),
    INDEX idx_role_status (role, status),
    INDEX idx_created (created_at),
    FULLTEXT INDEX idx_name_search (first_name, last_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- TELEGRAM СВЯЗЬ
-- =====================================================

CREATE TABLE telegram_connections (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    telegram_id BIGINT UNIQUE NOT NULL,
    telegram_username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    language_code VARCHAR(10),
    is_bot BOOLEAN DEFAULT FALSE,
    is_premium BOOLEAN DEFAULT FALSE,
    photo_url TEXT,
    auth_date TIMESTAMP,
    last_interaction TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_telegram_id (telegram_id),
    INDEX idx_username (telegram_username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- ПРОФИЛИ МАСТЕРОВ
-- =====================================================

CREATE TABLE master_profiles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT UNIQUE NOT NULL,
    
    -- Business info
    business_name VARCHAR(255),
    business_description TEXT,
    short_description VARCHAR(500),
    experience_years INT,
    specialization TEXT,
    work_places TEXT,
    
    -- Verification
    verified BOOLEAN DEFAULT FALSE,
    verification_date TIMESTAMP NULL,
    verified_by INT,
    verification_documents JSON,
    verification_level ENUM('basic', 'pro', 'expert') DEFAULT 'basic',
    
    -- Statistics
    rating DECIMAL(3,2) DEFAULT 0,
    reviews_count INT DEFAULT 0,
    completed_orders INT DEFAULT 0,
    cancelled_orders INT DEFAULT 0,
    response_rate INT DEFAULT 100,
    response_time INT DEFAULT 30, -- minutes
    avg_completion_time INT, -- minutes
    
    -- Pricing
    min_price DECIMAL(10,2),
    max_price DECIMAL(10,2),
    price_negotiable BOOLEAN DEFAULT FALSE,
    payment_methods JSON,
    commission_rate DECIMAL(5,2) DEFAULT 10.00,
    
    -- Availability
    is_online BOOLEAN DEFAULT FALSE,
    last_active TIMESTAMP NULL,
    work_schedule JSON, -- Weekly schedule
    days_off JSON, -- Vacations, holidays
    emergency_available BOOLEAN DEFAULT FALSE,
    
    -- Preferences
    auto_accept_orders BOOLEAN DEFAULT FALSE,
    max_orders_per_day INT DEFAULT 3,
    max_distance_km INT DEFAULT 20,
    notification_preferences JSON,
    
    -- SEO
    seo_keywords TEXT,
    seo_description TEXT,
    seo_rating DECIMAL(3,2) DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (verified_by) REFERENCES users(id) ON DELETE SET NULL,
    
    INDEX idx_rating (rating DESC),
    INDEX idx_verified (verified),
    INDEX idx_location_status (is_online),
    INDEX idx_completed_orders (completed_orders DESC),
    FULLTEXT INDEX idx_business_search (business_name, business_description, specialization)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- КАТЕГОРИИ УСЛУГ
-- =====================================================

CREATE TABLE service_categories (
    id INT PRIMARY KEY AUTO_INCREMENT,
    parent_id INT,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    icon VARCHAR(255),
    image_url TEXT,
    description TEXT,
    meta_title VARCHAR(255),
    meta_description TEXT,
    meta_keywords TEXT,
    sort_order INT DEFAULT 0,
    is_popular BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (parent_id) REFERENCES service_categories(id) ON DELETE CASCADE,
    INDEX idx_parent (parent_id),
    INDEX idx_slug (slug),
    INDEX idx_popular (is_popular)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- УСЛУГИ
-- =====================================================

CREATE TABLE services (
    id INT PRIMARY KEY AUTO_INCREMENT,
    master_id INT NOT NULL,
    category_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    description TEXT,
    short_description VARCHAR(500),
    
    -- Pricing
    price_type ENUM('fixed', 'hourly', 'negotiable', 'from') DEFAULT 'fixed',
    price DECIMAL(10,2),
    old_price DECIMAL(10,2),
    min_price DECIMAL(10,2),
    max_price DECIMAL(10,2),
    price_description TEXT,
    payment_options JSON,
    
    -- Duration
    duration_minutes INT,
    min_duration INT,
    max_duration INT,
    emergency_duration INT,
    
    -- Media
    images JSON,
    videos JSON,
    documents JSON,
    thumbnail VARCHAR(500),
    
    -- Features
    features JSON,
    requirements TEXT,
    included_items TEXT,
    not_included TEXT,
    
    -- Logistics
    is_online BOOLEAN DEFAULT FALSE,
    is_offline BOOLEAN DEFAULT TRUE,
    client_location_required BOOLEAN DEFAULT TRUE,
    travel_fee DECIMAL(10,2) DEFAULT 0,
    travel_distance_km INT,
    
    -- Statistics
    views_count INT DEFAULT 0,
    orders_count INT DEFAULT 0,
    rating DECIMAL(3,2) DEFAULT 0,
    reviews_count INT DEFAULT 0,
    
    -- Flags
    is_popular BOOLEAN DEFAULT FALSE,
    is_promoted BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    promotion_end_date TIMESTAMP NULL,
    
    -- SEO
    seo_title VARCHAR(255),
    seo_description TEXT,
    seo_keywords TEXT,
    seo_h1 VARCHAR(255),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (master_id) REFERENCES master_profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES service_categories(id),
    
    UNIQUE KEY unique_master_service (master_id, slug),
    INDEX idx_category (category_id),
    INDEX idx_master (master_id),
    INDEX idx_price (price),
    INDEX idx_popular (is_popular),
    INDEX idx_rating (rating DESC),
    FULLTEXT INDEX idx_service_search (name, description, short_description)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- ГЕО-ДАННЫЕ
-- =====================================================

CREATE TABLE cities (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    region VARCHAR(255),
    country VARCHAR(100) DEFAULT 'Россия',
    country_code VARCHAR(2) DEFAULT 'RU',
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    timezone VARCHAR(50),
    is_capital BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    population INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_name (name),
    INDEX idx_coords (latitude, longitude),
    INDEX idx_region (region)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE districts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    city_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    polygon_geometry JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (city_id) REFERENCES cities(id) ON DELETE CASCADE,
    INDEX idx_city_name (city_id, name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE master_addresses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    master_id INT NOT NULL,
    address_type ENUM('main', 'additional', 'temporary') DEFAULT 'main',
    city_id INT NOT NULL,
    district_id INT,
    
    address_line TEXT NOT NULL,
    entrance VARCHAR(50),
    floor INT,
    apartment VARCHAR(50),
    postal_code VARCHAR(20),
    
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    google_place_id VARCHAR(255),
    yandex_place_id VARCHAR(255),
    
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (master_id) REFERENCES master_profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (city_id) REFERENCES cities(id),
    FOREIGN KEY (district_id) REFERENCES districts(id),
    
    INDEX idx_master_location (master_id, is_active),
    INDEX idx_coords (latitude, longitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE service_areas (
    id INT PRIMARY KEY AUTO_INCREMENT,
    master_id INT NOT NULL,
    city_id INT NOT NULL,
    district_id INT,
    radius_km INT DEFAULT 10,
    custom_polygon JSON,
    price_multiplier DECIMAL(3,2) DEFAULT 1.00,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (master_id) REFERENCES master_profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (city_id) REFERENCES cities(id),
    FOREIGN KEY (district_id) REFERENCES districts(id),
    
    INDEX idx_master_area (master_id, city_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- ЗАКАЗЫ
-- =====================================================

CREATE TABLE orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    
    -- Participants
    client_id INT NOT NULL,
    master_id INT NOT NULL,
    service_id INT NOT NULL,
    address_id INT,
    
    -- Status
    status ENUM(
        'draft', 'pending', 'awaiting_payment', 'payment_verified',
        'confirmed', 'in_progress', 'completed', 'cancelled', 
        'refunded', 'disputed', 'archived'
    ) DEFAULT 'pending',
    payment_status ENUM('pending', 'paid', 'failed', 'refunded', 'partially_refunded') DEFAULT 'pending',
    
    -- Schedule
    scheduled_date DATE NOT NULL,
    scheduled_time TIME NOT NULL,
    scheduled_end_time TIME,
    actual_start_time TIMESTAMP NULL,
    actual_end_time TIMESTAMP NULL,
    duration_minutes INT,
    
    -- Financial
    service_price DECIMAL(10,2) NOT NULL,
    additional_price DECIMAL(10,2) DEFAULT 0,
    travel_fee DECIMAL(10,2) DEFAULT 0,
    discount_amount DECIMAL(10,2) DEFAULT 0,
    total_amount DECIMAL(10,2) NOT NULL,
    platform_commission DECIMAL(10,2),
    master_earnings DECIMAL(10,2),
    
    -- Payment
    payment_method VARCHAR(50),
    payment_id VARCHAR(255),
    payment_details JSON,
    
    -- Communications
    client_comment TEXT,
    master_comment TEXT,
    admin_comment TEXT,
    client_contact_preference JSON,
    
    -- Ratings
    client_rating TINYINT,
    client_review TEXT,
    client_review_date TIMESTAMP NULL,
    master_rating TINYINT,
    master_review TEXT,
    master_review_date TIMESTAMP NULL,
    
    -- Flags
    is_emergency BOOLEAN DEFAULT FALSE,
    is_express BOOLEAN DEFAULT FALSE,
    is_first_order BOOLEAN DEFAULT FALSE,
    is_repeat_client BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    cancelled_at TIMESTAMP NULL,
    cancelled_by INT,
    cancel_reason TEXT,
    
    FOREIGN KEY (client_id) REFERENCES users(id),
    FOREIGN KEY (master_id) REFERENCES master_profiles(id),
    FOREIGN KEY (service_id) REFERENCES services(id),
    FOREIGN KEY (address_id) REFERENCES master_addresses(id),
    FOREIGN KEY (cancelled_by) REFERENCES users(id),
    
    INDEX idx_status (status),
    INDEX idx_client (client_id),
    INDEX idx_master (master_id),
    INDEX idx_schedule (scheduled_date, scheduled_time),
    INDEX idx_payment (payment_status),
    INDEX idx_rating (master_rating),
    INDEX idx_created (created_at),
    INDEX idx_completed (completed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE order_status_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    status VARCHAR(50) NOT NULL,
    comment TEXT,
    changed_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (changed_by) REFERENCES users(id),
    
    INDEX idx_order_status (order_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE order_timeline (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    INDEX idx_order_events (order_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- ПЛАТЕЖИ
-- =====================================================

CREATE TABLE payments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    payment_number VARCHAR(100) UNIQUE NOT NULL,
    
    -- Payment details
    payment_method ENUM('card', 'cash', 'stripe', 'paypal', 'apple_pay', 
                        'google_pay', 'bank_transfer', 'crypto', 'wallet') NOT NULL,
    provider VARCHAR(50),
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'RUB',
    
    -- Status
    status ENUM('pending', 'processing', 'completed', 'failed', 'refunded', 'cancelled') DEFAULT 'pending',
    
    -- Transaction
    transaction_id VARCHAR(255),
    external_id VARCHAR(255),
    gateway_response JSON,
    
    -- Refund
    refund_amount DECIMAL(10,2) DEFAULT 0,
    refund_reason TEXT,
    refunded_at TIMESTAMP NULL,
    refunded_by INT,
    
    -- Metadata
    metadata JSON,
    paid_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (refunded_by) REFERENCES users(id),
    
    INDEX idx_order (order_id),
    INDEX idx_transaction (transaction_id),
    INDEX idx_status (status),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE payment_methods (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    method_type VARCHAR(50) NOT NULL,
    provider VARCHAR(50),
    token VARCHAR(255),
    last_digits VARCHAR(4),
    card_brand VARCHAR(50),
    card_holder VARCHAR(255),
    expiry_month INT,
    expiry_year INT,
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user (user_id, is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- ОТЗЫВЫ И РЕЙТИНГИ
-- =====================================================

CREATE TABLE reviews (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT UNIQUE NOT NULL,
    reviewer_id INT NOT NULL,
    reviewee_id INT NOT NULL,
    
    -- Rating
    quality_rating TINYINT CHECK (quality_rating BETWEEN 1 AND 5),
    price_rating TINYINT CHECK (price_rating BETWEEN 1 AND 5),
    communication_rating TINYINT CHECK (communication_rating BETWEEN 1 AND 5),
    punctuality_rating TINYINT CHECK (punctuality_rating BETWEEN 1 AND 5),
    overall_rating TINYINT NOT NULL CHECK (overall_rating BETWEEN 1 AND 5),
    
    -- Content
    title VARCHAR(255),
    content TEXT,
    pros TEXT,
    cons TEXT,
    recommendation BOOLEAN DEFAULT TRUE,
    
    -- Media
    images JSON,
    videos JSON,
    
    -- Statistics
    likes_count INT DEFAULT 0,
    dislikes_count INT DEFAULT 0,
    comments_count INT DEFAULT 0,
    
    -- Flags
    is_verified BOOLEAN DEFAULT FALSE,
    is_anonymous BOOLEAN DEFAULT FALSE,
    is_purchased BOOLEAN DEFAULT TRUE,
    is_edited BOOLEAN DEFAULT FALSE,
    
    -- Moderation
    status ENUM('pending', 'approved', 'rejected', 'hidden') DEFAULT 'pending',
    moderator_comment TEXT,
    moderated_by INT,
    moderated_at TIMESTAMP NULL,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewer_id) REFERENCES users(id),
    FOREIGN KEY (reviewee_id) REFERENCES users(id),
    FOREIGN KEY (moderated_by) REFERENCES users(id),
    
    INDEX idx_reviewee (reviewee_id, overall_rating),
    INDEX idx_status (status),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE review_comments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    review_id INT NOT NULL,
    user_id INT NOT NULL,
    comment TEXT NOT NULL,
    likes_count INT DEFAULT 0,
    is_edited BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (review_id) REFERENCES reviews(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    
    INDEX idx_review (review_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE review_likes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    review_id INT NOT NULL,
    user_id INT NOT NULL,
    like_type ENUM('like', 'dislike') DEFAULT 'like',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (review_id) REFERENCES reviews(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    
    UNIQUE KEY unique_user_review (user_id, review_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- УВЕДОМЛЕНИЯ
-- =====================================================

CREATE TABLE notifications (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    type VARCHAR(100) NOT NULL,
    channel ENUM('telegram', 'email', 'sms', 'push', 'web') DEFAULT 'telegram',
    
    -- Content
    title VARCHAR(255),
    message TEXT NOT NULL,
    data JSON,
    
    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    is_sent BOOLEAN DEFAULT FALSE,
    is_delivered BOOLEAN DEFAULT FALSE,
    is_clicked BOOLEAN DEFAULT FALSE,
    
    -- Timing
    scheduled_for TIMESTAMP NULL,
    sent_at TIMESTAMP NULL,
    delivered_at TIMESTAMP NULL,
    read_at TIMESTAMP NULL,
    clicked_at TIMESTAMP NULL,
    
    -- Priority
    priority ENUM('low', 'normal', 'high', 'urgent') DEFAULT 'normal',
    
    -- Metadata
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    INDEX idx_user_read (user_id, is_read),
    INDEX idx_type (type),
    INDEX idx_scheduled (scheduled_for),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE notification_templates (
    id INT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255),
    subject VARCHAR(255),
    telegram_template TEXT,
    email_template TEXT,
    sms_template TEXT,
    push_template TEXT,
    web_template TEXT,
    variables JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE notification_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    notification_id INT NOT NULL,
    channel VARCHAR(50),
    provider_response JSON,
    status VARCHAR(50),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (notification_id) REFERENCES notifications(id) ON DELETE CASCADE,
    INDEX idx_notification (notification_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- ИНТЕГРАЦИЯ С CRM
-- =====================================================

CREATE TABLE crm_integrations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    master_id INT NOT NULL,
    crm_type ENUM('amocrm', 'bitrix24', 'yandex', 'custom') NOT NULL,
    
    -- Connection
    api_url VARCHAR(500),
    api_key VARCHAR(500),
    api_secret VARCHAR(500),
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP NULL,
    
    -- Settings
    sync_settings JSON,
    field_mapping JSON,
    webhook_url VARCHAR(500),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_sync TIMESTAMP NULL,
    sync_status VARCHAR(50),
    error_message TEXT,
    
    -- Statistics
    synced_leads INT DEFAULT 0,
    synced_contacts INT DEFAULT 0,
    synced_deals INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (master_id) REFERENCES master_profiles(id) ON DELETE CASCADE,
    INDEX idx_master (master_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE crm_sync_queue (
    id INT PRIMARY KEY AUTO_INCREMENT,
    integration_id INT NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INT NOT NULL,
    action ENUM('create', 'update', 'delete') DEFAULT 'create',
    data JSON,
    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    attempts INT DEFAULT 0,
    error_message TEXT,
    synced_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (integration_id) REFERENCES crm_integrations(id) ON DELETE CASCADE,
    INDEX idx_status (status),
    INDEX idx_entity (entity_type, entity_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- АНАЛИТИКА И ТРЕКИНГ
-- =====================================================

CREATE TABLE analytics_events (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    telegram_id BIGINT,
    event_type VARCHAR(100) NOT NULL,
    event_category VARCHAR(100),
    event_action VARCHAR(100),
    event_label VARCHAR(255),
    event_value INT,
    
    -- Context
    page_url VARCHAR(500),
    referrer VARCHAR(500),
    user_agent TEXT,
    ip_address VARCHAR(45),
    session_id VARCHAR(100),
    
    -- Data
    event_data JSON,
    metadata JSON,
    
    -- Device
    device_type VARCHAR(50),
    browser VARCHAR(100),
    os VARCHAR(100),
    screen_resolution VARCHAR(20),
    
    -- Location
    country VARCHAR(100),
    city VARCHAR(100),
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    
    -- Timing
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    
    INDEX idx_event_type (event_type),
    INDEX idx_user (user_id),
    INDEX idx_telegram (telegram_id),
    INDEX idx_session (session_id),
    INDEX idx_created (created_at),
    INDEX idx_category_action (event_category, event_action)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE analytics_daily_stats (
    id INT PRIMARY KEY AUTO_INCREMENT,
    stat_date DATE NOT NULL,
    
    -- Users
    new_users INT DEFAULT 0,
    active_users INT DEFAULT 0,
    new_masters INT DEFAULT 0,
    active_masters INT DEFAULT 0,
    
    -- Orders
    total_orders INT DEFAULT 0,
    completed_orders INT DEFAULT 0,
    cancelled_orders INT DEFAULT 0,
    avg_order_value DECIMAL(10,2) DEFAULT 0,
    total_revenue DECIMAL(15,2) DEFAULT 0,
    
    -- Services
    total_services INT DEFAULT 0,
    total_views INT DEFAULT 0,
    unique_viewers INT DEFAULT 0,
    
    -- Telegram
    bot_starts INT DEFAULT 0,
    bot_commands INT DEFAULT 0,
    bot_messages INT DEFAULT 0,
    unique_users INT DEFAULT 0,
    
    -- Marketing
    ad_clicks INT DEFAULT 0,
    ad_views INT DEFAULT 0,
    conversion_rate DECIMAL(5,2) DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_date (stat_date),
    INDEX idx_date (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- SEO И МАРКЕТИНГ
-- =====================================================

CREATE TABLE seo_keywords (
    id INT PRIMARY KEY AUTO_INCREMENT,
    keyword VARCHAR(255) NOT NULL,
    category_id INT,
    search_volume INT DEFAULT 0,
    competition DECIMAL(5,2) DEFAULT 0,
    avg_position DECIMAL(5,2) DEFAULT 0,
    cpc DECIMAL(10,2) DEFAULT 0,
    relevance_score DECIMAL(5,2) DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (category_id) REFERENCES service_categories(id) ON DELETE SET NULL,
    INDEX idx_keyword (keyword),
    INDEX idx_volume (search_volume DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE seo_rankings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    keyword_id INT NOT NULL,
    master_id INT,
    service_id INT,
    position INT,
    previous_position INT,
    url VARCHAR(500),
    search_engine VARCHAR(50) DEFAULT 'google',
    check_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (keyword_id) REFERENCES seo_keywords(id) ON DELETE CASCADE,
    FOREIGN KEY (master_id) REFERENCES master_profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    
    INDEX idx_keyword_date (keyword_id, check_date),
    INDEX idx_master (master_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- AI И МАШИННОЕ ОБУЧЕНИЕ
-- =====================================================

CREATE TABLE ai_models (
    id INT PRIMARY KEY AUTO_INCREMENT,
    model_name VARCHAR(255) NOT NULL,
    model_type VARCHAR(100) NOT NULL,
    model_version VARCHAR(50),
    model_path TEXT,
    accuracy DECIMAL(5,2),
    trained_at TIMESTAMP,
    training_duration INT,
    training_samples INT,
    is_active BOOLEAN DEFAULT FALSE,
    parameters JSON,
    metrics JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE ai_predictions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    model_id INT NOT NULL,
    prediction_type VARCHAR(100) NOT NULL,
    input_data JSON,
    output_data JSON,
    confidence DECIMAL(5,2),
    processing_time_ms INT,
    user_id INT,
    order_id INT,
    is_correct BOOLEAN,
    feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (model_id) REFERENCES ai_models(id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL,
    
    INDEX idx_type (prediction_type),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE ai_chat_history (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    telegram_id BIGINT,
    session_id VARCHAR(100) NOT NULL,
    
    -- Message
    message TEXT NOT NULL,
    message_type ENUM('text', 'voice', 'photo', 'video') DEFAULT 'text',
    language VARCHAR(10),
    
    -- AI Response
    response TEXT NOT NULL,
    intent VARCHAR(100),
    confidence DECIMAL(5,2),
    tokens_used INT,
    processing_time_ms INT,
    
    -- Context
    context JSON,
    suggested_actions JSON,
    
    -- Feedback
    feedback BOOLEAN,
    feedback_text TEXT,
    
    -- Metadata
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    
    INDEX idx_session (session_id),
    INDEX idx_user_date (user_id, created_at),
    INDEX idx_intent (intent)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- TELEGRAM ПРОДВИЖЕНИЕ
-- =====================================================

CREATE TABLE tg_target_groups (
    id INT PRIMARY KEY AUTO_INCREMENT,
    group_id BIGINT NOT NULL,
    group_name VARCHAR(255),
    group_username VARCHAR(255),
    invite_link VARCHAR(500),
    members_count INT DEFAULT 0,
    members_online INT DEFAULT 0,
    group_type ENUM('public', 'private', 'supergroup') DEFAULT 'public',
    category VARCHAR(100),
    description TEXT,
    language VARCHAR(10),
    country VARCHAR(100),
    city VARCHAR(100),
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    priority INT DEFAULT 5,
    last_ad_date TIMESTAMP NULL,
    ad_frequency_days INT DEFAULT 7,
    ad_sent_count INT DEFAULT 0,
    ad_success_rate DECIMAL(5,2) DEFAULT 0,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_group_id (group_id),
    INDEX idx_category (category),
    INDEX idx_members (members_count DESC),
    INDEX idx_active (is_active),
    INDEX idx_last_ad (last_ad_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE tg_ad_campaigns (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    campaign_type ENUM('mass', 'targeted', 'smart') DEFAULT 'targeted',
    
    -- Content
    ad_text TEXT NOT NULL,
    ad_media TEXT,
    ad_buttons JSON,
    ad_link VARCHAR(500),
    
    -- Targeting
    target_categories JSON,
    target_languages JSON,
    target_countries JSON,
    target_cities JSON,
    min_members INT DEFAULT 100,
    max_members INT DEFAULT 1000000,
    
    -- Schedule
    schedule_type ENUM('daily', 'weekly', 'once') DEFAULT 'daily',
    schedule_time TIME,
    frequency_days INT DEFAULT 7,
    start_date DATE,
    end_date DATE,
    
    -- Budget
    budget_type ENUM('unlimited', 'daily', 'total') DEFAULT 'unlimited',
    daily_budget DECIMAL(10,2),
    total_budget DECIMAL(10,2),
    cost_per_ad DECIMAL(10,2) DEFAULT 0,
    
    -- AI Optimization
    ai_optimization BOOLEAN DEFAULT TRUE,
    ai_instructions TEXT,
    ai_model VARCHAR(100),
    
    -- Statistics
    total_sent INT DEFAULT 0,
    total_groups INT DEFAULT 0,
    total_views INT DEFAULT 0,
    total_clicks INT DEFAULT 0,
    total_conversions INT DEFAULT 0,
    conversion_rate DECIMAL(5,2) DEFAULT 0,
    total_spent DECIMAL(10,2) DEFAULT 0,
    
    -- Status
    status ENUM('draft', 'active', 'paused', 'completed', 'archived') DEFAULT 'draft',
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Metadata
    metadata JSON,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
   