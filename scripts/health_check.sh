#!/usr/bin/env python3
import sys
import asyncio
import asyncpg
import os
import time
import json
from datetime import datetime

async def health_check():
    """Комплексная проверка состояния системы"""
    health_status = {
        "timestamp": datetime.now().isoformat(),
        "bot_status": "unknown",
        "database_status": "unknown",
        "memory_usage": "unknown",
        "disk_usage": "unknown",
        "response_time": 0,
        "errors": [],
        "warnings": []
    }

    start_time = time.time()

    try:
        # Проверка подключения к БД
        conn = await asyncpg.connect(
            host=os.getenv('DB_HOST', 'postgres'),
            port=int(os.getenv('DB_PORT', 5432)),
            user=os.getenv('DB_USER', 'festival_user'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'festival_bot'),
            timeout=5
        )

        await conn.fetchval('SELECT 1')

        # Расширенная проверка БД
        try:
            # Размер БД
            db_size = await conn.fetchval("""
                SELECT pg_size_pretty(pg_database_size(current_database()))
            """)

            # Активные соединения
            active_connections = await conn.fetchval("""
                SELECT count(*) FROM pg_stat_activity
                WHERE state = 'active' AND datname = current_database()
            """)

            # Проверка основных таблиц
            tables_exist = await conn.fetchval("""
                SELECT count(*) FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('users', 'support_tickets', 'feedback', 'schedule')
            """)

            health_status["database_status"] = "healthy"
            health_status["database_info"] = {
                "size": db_size,
                "active_connections": active_connections,
                "core_tables": tables_exist
            }

            if tables_exist < 4:
                health_status["warnings"].append(f"Missing core tables: {4 - tables_exist}")

        except Exception as e:
            health_status["warnings"].append(f"Database metrics error: {str(e)}")

        await conn.close()

    except Exception as e:
        health_status["database_status"] = "error"
        health_status["errors"].append(f"Database error: {str(e)}")

    # Проверка использования памяти
    try:
        import psutil

        # Информация о процессе
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()
        cpu_percent = process.cpu_percent(interval=1)

        # Системная информация
        system_memory = psutil.virtual_memory()
        disk_usage = psutil.disk_usage('/')

        health_status["memory_usage"] = {
            "process_rss_mb": round(memory_info.rss / 1024 / 1024, 2),
            "process_vms_mb": round(memory_info.vms / 1024 / 1024, 2),
            "process_percent": round(memory_percent, 2),
            "system_total_gb": round(system_memory.total / 1024 / 1024 / 1024, 2),
            "system_available_gb": round(system_memory.available / 1024 / 1024 / 1024, 2),
            "system_percent": system_memory.percent
        }

        health_status["cpu_usage"] = {
            "process_percent": round(cpu_percent, 2),
            "system_percent": round(psutil.cpu_percent(interval=1), 2)
        }

        health_status["disk_usage"] = {
            "total_gb": round(disk_usage.total / 1024 / 1024 / 1024, 2),
            "free_gb": round(disk_usage.free / 1024 / 1024 / 1024, 2),
            "used_percent": round((disk_usage.used / disk_usage.total) * 100, 2)
        }

        # Предупреждения
        if memory_percent > 80:
            health_status["warnings"].append(f"High process memory usage: {memory_percent:.1f}%")

        if system_memory.percent > 90:
            health_status["warnings"].append(f"High system memory usage: {system_memory.percent:.1f}%")

        if disk_usage.free < 1024 * 1024 * 1024:  # Менее 1GB свободного места
            health_status["warnings"].append(f"Low disk space: {disk_usage.free / 1024 / 1024 / 1024:.1f}GB free")

    except ImportError:
        health_status["memory_usage"] = "psutil not available"
        health_status["errors"].append("psutil package not installed")
    except Exception as e:
        health_status["warnings"].append(f"System metrics error: {str(e)}")

    # Проверка файловой системы
    try:
        # Проверка важных директорий
        required_dirs = ['/app/logs', '/app/backups', '/app/src']
        for dir_path in required_dirs:
            if not os.path.exists(dir_path):
                health_status["warnings"].append(f"Missing directory: {dir_path}")
            elif not os.access(dir_path, os.W_OK):
                health_status["warnings"].append(f"No write access to: {dir_path}")

        # Проверка важных файлов
        required_files = ['/app/src/main.py', '/app/src/config.py']
        for file_path in required_files:
            if not os.path.exists(file_path):
                health_status["errors"].append(f"Missing critical file: {file_path}")

    except Exception as e:
        health_status["warnings"].append(f"Filesystem check error: {str(e)}")

    # Проверка состояния поддержки (если БД доступна)
    if health_status["database_status"] == "healthy":
        try:
            conn = await asyncpg.connect(
                host=os.getenv('DB_HOST', 'postgres'),
                port=int(os.getenv('DB_PORT', 5432)),
                user=os.getenv('DB_USER', 'festival_user'),
                password=os.getenv('DB_PASSWORD'),
                database=os.getenv('DB_NAME', 'festival_bot'),
                timeout=5
            )

            # Количество открытых тикетов
            open_tickets = await conn.fetchval(
                "SELECT COUNT(*) FROM support_tickets WHERE is_closed = FALSE"
            )

            # Количество срочных тикетов (без ответа > 2 часов)
            urgent_tickets = await conn.fetchval("""
                SELECT COUNT(*) FROM support_tickets
                WHERE is_closed = FALSE
                AND (last_staff_response_at IS NULL OR last_user_message_at > last_staff_response_at)
                AND last_user_message_at < NOW() - INTERVAL '2 hours'
            """)

            # Общее количество пользователей
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")

            # Отзывы за последние 24 часа
            recent_feedback = await conn.fetchval("""
                SELECT COUNT(*) FROM feedback
                WHERE created_at > NOW() - INTERVAL '24 hours'
            """)

            health_status["support_health"] = {
                "open_tickets": open_tickets,
                "urgent_tickets": urgent_tickets,
                "total_users": total_users,
                "recent_feedback_24h": recent_feedback
            }

            # Предупреждения по поддержке
            if urgent_tickets > 10:
                health_status["warnings"].append(f"Many urgent tickets: {urgent_tickets}")

            if open_tickets > 50:
                health_status["warnings"].append(f"Many open tickets: {open_tickets}")

            if urgent_tickets > 0:
                health_status["warnings"].append(f"Urgent tickets require attention: {urgent_tickets}")

            await conn.close()

        except Exception as e:
            health_status["warnings"].append(f"Support health check error: {str(e)}")

    # Проверка времени отклика
    end_time = time.time()
    response_time = round((end_time - start_time) * 1000, 2)  # в миллисекундах
    health_status["response_time"] = response_time

    if response_time > 5000:  # более 5 секунд
        health_status["warnings"].append(f"Slow response time: {response_time}ms")
    elif response_time > 2000:  # более 2 секунд
        health_status["warnings"].append(f"Moderate response time: {response_time}ms")

    # Общее состояние
    is_healthy = len(health_status["errors"]) == 0
    has_warnings = len(health_status["warnings"]) > 0

    # Определяем статус
    if is_healthy and not has_warnings:
        overall_status = "healthy"
        status_emoji = "✅"
    elif is_healthy and has_warnings:
        overall_status = "healthy_with_warnings"
        status_emoji = "⚠️"
    else:
        overall_status = "unhealthy"
        status_emoji = "❌"

    health_status["overall_status"] = overall_status

    # Вывод результата
    print(f"{status_emoji} Health check completed at {health_status['timestamp']}")
    print(f"📊 Overall status: {overall_status}")
    print(f"⏱️  Response time: {response_time}ms")

    if health_status["database_status"] == "healthy":
        print(f"💾 Database: {health_status['database_info'].get('size', 'unknown')}")

    if "memory_usage" in health_status and isinstance(health_status["memory_usage"], dict):
        print(f"🧠 Memory: {health_status['memory_usage']['process_rss_mb']}MB process, "
              f"{health_status['memory_usage']['system_percent']}% system")

    if "support_health" in health_status:
        support = health_status["support_health"]
        print(f"🎫 Support: {support['open_tickets']} open tickets, {support['urgent_tickets']} urgent")

    if has_warnings:
        print(f"⚠️  Warnings ({len(health_status['warnings'])}):")
        for warning in health_status['warnings']:
            print(f"   • {warning}")

    if health_status["errors"]:
        print(f"🚨 Errors ({len(health_status['errors'])}):")
        for error in health_status['errors']:
            print(f"   • {error}")

    # Вывод JSON для машинного чтения (если нужно)
    verbose = os.getenv('HEALTH_CHECK_VERBOSE', 'false').lower() == 'true'
    if verbose:
        print(f"\n📋 Full health status JSON:")
        print(json.dumps(health_status, indent=2, ensure_ascii=False))

    # Возвращаем код: 0 = здоров, 1 = болен
    return 0 if is_healthy else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(health_check())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Health check interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Health check crashed: {e}")
        sys.exit(1)