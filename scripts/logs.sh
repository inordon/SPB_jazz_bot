cat > scripts/logs.sh << 'EOF'
#!/bin/bash

# Функция для отображения меню
show_menu() {
    echo "📋 Festival Bot Logs"
    echo "==================="
    echo "1) Bot logs (main)"
    echo "2) Error logs"
    echo "3) Support logs"
    echo "4) Stats logs"
    echo "5) All logs (live)"
    echo "6) Clear all logs"
    echo "q) Quit"
    echo
}

# Функция для очистки логов
clear_logs() {
    read -p "⚠️ Are you sure you want to clear all logs? [y/N]: " confirm
    if [[ $confirm =~ ^[Yy]$ ]]; then
        rm -f /app/logs/*.log
        echo "✅ All logs cleared!"
    else
        echo "❌ Operation cancelled."
    fi
}

while true; do
    show_menu
    read -p "Choose option: " choice

    case $choice in
        1)
            echo "📄 Bot logs:"
            tail -f /app/logs/bot.log 2>/dev/null || echo "No bot logs found"
            ;;
        2)
            echo "❌ Error logs:"
            tail -f /app/logs/errors.log 2>/dev/null || echo "No error logs found"
            ;;
        3)
            echo "🆘 Support logs:"
            tail -f /app/logs/support.log 2>/dev/null || echo "No support logs found"
            ;;
        4)
            echo "📊 Stats logs:"
            tail -f /app/logs/stats.log 2>/dev/null || echo "No stats logs found"
            ;;
        5)
            echo "📋 All logs (live):"
            tail -f /app/logs/*.log 2>/dev/null || echo "No logs found"
            ;;
        6)
            clear_logs
            ;;
        q|Q)
            echo "👋 Goodbye!"
            exit 0
            ;;
        *)
            echo "❌ Invalid option"
            ;;
    esac

    echo
    read -p "Press Enter to continue..."
    clear
done
EOF