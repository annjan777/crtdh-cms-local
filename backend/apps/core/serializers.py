from rest_framework import serializers

from .models import AboutPage, FocusArea, HomePage, NavItem, NewsItem, ObjectiveRow, SiteSettings, TimelineEntry


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = [
            "id",
            "address",
            "phone_primary",
            "phone_secondary",
            "email_primary",
            "email_secondary",
            "map_embed_url",
            "facebook_url",
            "linkedin_url",
            "instagram_url",
            "twitter_url",
            "logo_left",
            "logo_right",
            "site_logo",
        ]
        read_only_fields = ["id"]


class AboutPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AboutPage
        fields = [
            "id",
            "intro",
            "mission_vision",
            "focus_intro",
            "ecosystem_heading",
            "ecosystem_image",
            "pi_desk_image",
            "pi_desk_document",
            "dsir_about",
            "iitkgp_about",
        ]
        read_only_fields = ["id"]


class HomePageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomePage
        fields = [
            "id",
            "objective_text",
            "enterprises_text",
            "enterprises_image_1",
            "enterprises_image_2",
            "msme_map_image",
            "msme_caption",
            "women_text_1",
            "women_image_1",
            "women_image_2",
            "women_text_2",
            "location_address",
            "location_description",
            "facility_card_1_title",
            "facility_card_1_image",
            "facility_card_1_link",
            "facility_card_2_title",
            "facility_card_2_image",
            "facility_card_2_link",
            "facility_card_3_title",
            "facility_card_3_image",
            "facility_card_3_link",
            "chintan_shivir_youtube_id",
            "viksit_bharat_youtube_id",
            "office_image",
            "membership_heading",
            "membership_pdf",
        ]
        read_only_fields = ["id"]


class NavItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = NavItem
        fields = ["id", "label", "url", "order"]


class NewsItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsItem
        fields = ["id", "text", "link_url", "order"]


class FocusAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = FocusArea
        fields = ["id", "title", "color", "order"]


class ObjectiveRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObjectiveRow
        fields = ["id", "category", "task", "outcome", "order"]


class TimelineEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = TimelineEntry
        fields = ["id", "year", "title", "image", "order"]
