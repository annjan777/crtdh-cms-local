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
            "logo_left", "logo_left_alt",
            "logo_right", "logo_right_alt",
            "site_logo", "site_logo_alt",
            "version",
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
            "ecosystem_image", "ecosystem_image_alt",
            "pi_desk_image", "pi_desk_image_alt",
            "pi_desk_document",
            "dsir_about",
            "iitkgp_about",
            "version",
        ]
        read_only_fields = ["id"]


class HomePageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomePage
        fields = [
            "id",
            "objective_text",
            "enterprises_text",
            "enterprises_image_1", "enterprises_image_1_alt",
            "enterprises_image_2", "enterprises_image_2_alt",
            "msme_map_image", "msme_map_image_alt",
            "msme_caption",
            "women_text_1",
            "women_image_1", "women_image_1_alt",
            "women_image_2", "women_image_2_alt",
            "women_text_2",
            "location_address",
            "location_description",
            "facility_card_1_title",
            "facility_card_1_image", "facility_card_1_image_alt",
            "facility_card_1_link",
            "facility_card_2_title",
            "facility_card_2_image", "facility_card_2_image_alt",
            "facility_card_2_link",
            "facility_card_3_title",
            "facility_card_3_image", "facility_card_3_image_alt",
            "facility_card_3_link",
            "chintan_shivir_youtube_id",
            "viksit_bharat_youtube_id",
            "office_image", "office_image_alt",
            "membership_heading",
            "membership_pdf",
            "pathway_1_title", "pathway_1_text", "pathway_1_link", "pathway_1_icon",
            "pathway_2_title", "pathway_2_text", "pathway_2_link", "pathway_2_icon",
            "pathway_3_title", "pathway_3_text", "pathway_3_link", "pathway_3_icon",
            "version",
        ]
        read_only_fields = ["id"]


class NavItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = NavItem
        fields = ["id", "label", "url", "order", "in_more", "is_published", "version"]


class NewsItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsItem
        fields = ["id", "text", "link_url", "order", "is_published", "version"]


class FocusAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = FocusArea
        fields = ["id", "title", "color", "order", "is_published", "version"]


class ObjectiveRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObjectiveRow
        fields = ["id", "category", "task", "outcome", "order", "is_published", "version"]


class TimelineEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = TimelineEntry
        fields = ["id", "year", "title", "image", "image_alt", "order", "is_published", "version"]
