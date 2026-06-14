from rest_framework import serializers


class StatisticsScopeSerializer(serializers.Serializer):
    """Серіалізатор області (масштабу) отриманих статистичних даних."""

    type = serializers.CharField(help_text="Область статистики: DORMITORY для адміністратора або FLOOR для модератора")
    dormitory_name = serializers.CharField(allow_null=True, help_text="Назва гуртожитку")
    floor_id = serializers.IntegerField(allow_null=True, help_text="ID поверху для модераторської статистики")
    floor_number = serializers.IntegerField(allow_null=True, help_text="Номер поверху для модераторської статистики")
    role = serializers.CharField(allow_null=True, help_text="Роль користувача, який запитує статистику")


class ResidentsStatisticsSerializer(serializers.Serializer):
    """Серіалізатор статистичних показників мешканців гуртожитку."""

    total = serializers.IntegerField(help_text="Загальна кількість користувачів у межах доступної області")
    activated = serializers.IntegerField(help_text="Кількість активованих користувачів")
    not_activated = serializers.IntegerField(help_text="Кількість користувачів, які ще не активували акаунт")
    moderators = serializers.IntegerField(help_text="Кількість модераторів")


class RoomsStatisticsSerializer(serializers.Serializer):
    """Серіалізатор статистичних показників кімнат."""

    total = serializers.IntegerField(help_text="Загальна кількість кімнат")
    living = serializers.IntegerField(help_text="Кількість житлових кімнат")
    blocked = serializers.IntegerField(help_text="Кількість заблокованих кімнат")
    full = serializers.IntegerField(help_text="Кількість повністю заповнених житлових кімнат")


class ResourcesStatisticsSerializer(serializers.Serializer):
    """Серіалізатор статистичних показників ресурсів."""

    total = serializers.IntegerField(help_text="Загальна кількість ресурсів")
    blocked = serializers.IntegerField(help_text="Кількість заблокованих ресурсів")


class TopResourceSerializer(serializers.Serializer):
    """Серіалізатор для окремого елемента топу популярних ресурсів."""

    resource_id = serializers.IntegerField(help_text="ID ресурсу")
    resource_name = serializers.CharField(help_text="Назва ресурсу")
    room_name = serializers.CharField(help_text="Кімната, де знаходиться ресурс")
    floor_number = serializers.IntegerField(help_text="Номер поверху")
    bookings_count = serializers.IntegerField(help_text="Кількість бронювань ресурсу")


class BookingsStatisticsSerializer(serializers.Serializer):
    """Серіалізатор статистичних показників бронювання ресурсів."""

    active = serializers.IntegerField(help_text="Кількість активних бронювань")
    today = serializers.IntegerField(help_text="Кількість активних бронювань на сьогодні")
    cancelled = serializers.IntegerField(help_text="Кількість скасованих бронювань")
    cancelled_by_residents = serializers.IntegerField(help_text="Скільки бронювань скасували самі мешканці")
    cancelled_by_moderators = serializers.IntegerField(help_text="Скільки бронювань скасували модератори")
    cancelled_by_admins = serializers.IntegerField(help_text="Скільки бронювань скасували адміністратори")
    top_resources = TopResourceSerializer(many=True, help_text="Найпопулярніші ресурси за кількістю бронювань")


class FloorActivitySerializer(serializers.Serializer):
    """Серіалізатор активностей на конкретному поверсі гуртожитку."""

    floor_id = serializers.IntegerField(help_text="ID поверху")
    floor_number = serializers.IntegerField(help_text="Номер поверху")
    residents_count = serializers.IntegerField(help_text="Кількість активованих мешканців")
    active_events_count = serializers.IntegerField(help_text="Кількість активних івентів")
    active_sharing_requests_count = serializers.IntegerField(help_text="Кількість активних запитів на шеринг")
    active_presence_count = serializers.IntegerField(help_text="Кількість активних позначок присутності")


class SocialStatisticsSerializer(serializers.Serializer):
    """Серіалізатор показників соціальної активності стрічки."""

    active_events = serializers.IntegerField(help_text="Кількість активних івентів")
    cancelled_events = serializers.IntegerField(help_text="Кількість скасованих івентів")
    active_sharing_requests = serializers.IntegerField(help_text="Кількість активних запитів на шеринг")
    completed_sharing_requests = serializers.IntegerField(help_text="Кількість виконаних запитів на шеринг")
    cancelled_sharing_requests = serializers.IntegerField(help_text="Кількість скасованих запитів на шеринг")
    floor_activity = FloorActivitySerializer(many=True, help_text="Активність по поверхах")


class AnnouncementsStatisticsSerializer(serializers.Serializer):
    """Серіалізатор показників активності оголошень."""

    active = serializers.IntegerField(help_text="Кількість активних оголошень")
    pinned = serializers.IntegerField(help_text="Кількість закріплених оголошень")
    total = serializers.IntegerField(help_text="Загальна кількість оголошень у межах доступної області")


class PresenceStatisticsSerializer(serializers.Serializer):
    """Серіалізатор показників відмітки присутності мешканців."""

    active = serializers.IntegerField(help_text="Кількість активних позначок присутності")


class StatisticsSummarySerializer(serializers.Serializer):
    """Консолідуючий серіалізатор для всього звіту статистики гуртожитку."""

    scope = StatisticsScopeSerializer(help_text="Область, для якої порахована статистика")
    residents = ResidentsStatisticsSerializer(help_text="Статистика мешканців")
    rooms = RoomsStatisticsSerializer(help_text="Статистика кімнат")
    resources = ResourcesStatisticsSerializer(help_text="Статистика ресурсів")
    bookings = BookingsStatisticsSerializer(help_text="Статистика бронювань")
    social = SocialStatisticsSerializer(help_text="Статистика соціальної активності")
    announcements = AnnouncementsStatisticsSerializer(help_text="Статистика оголошень")
    presence = PresenceStatisticsSerializer(help_text="Статистика присутності")
