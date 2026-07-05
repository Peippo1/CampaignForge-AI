import os
from pathlib import Path
import sys
from typing import Optional

# Add project root to sys.path for flexible imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

import pandas as pd
import streamlit as st

# Try importing pymysql and handle the error if it's missing
try:
    import pymysql  # noqa: F401
except ModuleNotFoundError:
    st.set_page_config(page_title="CampaignForge AI Dashboard", layout="wide")
    st.error("Required package 'pymysql' is not installed. Please check your environment.")
    st.stop()

from airflow.scripts.mysql_utils import get_customers_data
from genai.auth import AuthManager, AuthenticationError
from genai.schemas import (
    CampaignBrief,
    CampaignRegenerationRequest,
    ImageGenerationRequest,
    ImageReviewRequest,
)
from genai.service import CampaignBriefService, CampaignExportService, CampaignImageService
from genai.storage import CampaignStorage
from utils.crm_clients import HubSpotClient, SalesforceClient


st.set_page_config(page_title="CampaignForge AI Dashboard", layout="wide")
st.session_state["title_rendered"] = True
st.session_state["sidebar_initialized"] = True
campaign_storage = CampaignStorage()
auth_manager = AuthManager(campaign_storage)
campaign_brief_service = CampaignBriefService(storage=campaign_storage)
campaign_image_service = CampaignImageService(storage=campaign_storage)
campaign_export_service = CampaignExportService(storage=campaign_storage)


def render_styles():
    st.markdown(
        """
        <style>
            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(247, 205, 70, 0.18), transparent 30%),
                    radial-gradient(circle at top right, rgba(53, 122, 189, 0.14), transparent 28%),
                    linear-gradient(180deg, #f7f3ea 0%, #eef2f7 100%);
            }
            .hero-card {
                background: linear-gradient(135deg, #10233f 0%, #1f4a73 55%, #d8a73e 140%);
                color: #f8f5ef;
                padding: 1.6rem 1.8rem;
                border-radius: 20px;
                box-shadow: 0 18px 45px rgba(16, 35, 63, 0.16);
                margin-bottom: 1rem;
            }
            .hero-kicker {
                font-size: 0.8rem;
                letter-spacing: 0.18em;
                text-transform: uppercase;
                opacity: 0.78;
                margin-bottom: 0.6rem;
            }
            .hero-title {
                font-size: 2.2rem;
                font-weight: 700;
                line-height: 1.1;
                margin-bottom: 0.65rem;
            }
            .hero-copy {
                max-width: 52rem;
                font-size: 1rem;
                line-height: 1.55;
                opacity: 0.94;
            }
            .info-card {
                background: rgba(255, 255, 255, 0.82);
                border: 1px solid rgba(16, 35, 63, 0.08);
                border-radius: 16px;
                padding: 1rem 1.1rem;
                box-shadow: 0 10px 24px rgba(16, 35, 63, 0.07);
            }
            .section-label {
                font-size: 0.78rem;
                text-transform: uppercase;
                letter-spacing: 0.16em;
                color: #7b5b16;
                margin-bottom: 0.4rem;
                font-weight: 700;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def load_customer_data():
    try:
        return get_customers_data(), None
    except Exception as exc:
        return None, exc


def current_dashboard_principal():
    principal = st.session_state.get("dashboard_principal")
    if principal:
        return principal
    return auth_manager.demo_principal()


def require_dashboard_access():
    if not auth_manager.is_dashboard_auth_enabled():
        st.session_state["dashboard_principal"] = auth_manager.demo_principal()
        return

    if st.session_state.get("dashboard_principal"):
        return

    st.markdown("---")
    st.subheader("Hosted dashboard sign in")
    with st.form("dashboard-login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary")

    if submitted:
        try:
            st.session_state["dashboard_principal"] = auth_manager.authenticate_dashboard(
                username,
                password,
            )
            st.rerun()
        except AuthenticationError as exc:
            st.error(str(exc))
    st.stop()


def campaign_history_label(campaign) -> str:
    campaign_name = (
        campaign.brief.campaign_name or campaign.brief.product_name or "Untitled campaign"
    )
    return f"{campaign.campaign_id} | {campaign_name}"


def angle_option_label(angle) -> str:
    return f"{angle.angle_id} | {angle.title}"


def build_crm_records(dataframe: pd.DataFrame):
    records = []
    for idx, _ in dataframe.head(20).iterrows():
        records.append(
            {
                "LastName": f"Customer {idx}",
                "Company": "Marketing List",
                "Email": f"customer{idx}@example.com",
                "Recency": dataframe.loc[idx].get("Recency"),
                "Income": dataframe.loc[idx].get("Income"),
            }
        )
    return records


def display_campaign_details(manifest):
    st.markdown("**Campaign summary**")
    st.write(manifest.output.campaign_summary)

    st.markdown("**Audience suggestions**")
    for persona in manifest.output.audience_suggestions:
        st.markdown(f"- **{persona.name}**: {persona.description}")

    st.markdown("**Channel recommendations**")
    st.write(", ".join(manifest.output.channel_recommendations))

    for angle in manifest.output.angles:
        with st.expander(angle.title, expanded=False):
            st.write(angle.summary)
            st.markdown(f"**Tone:** {angle.tone}")
            st.markdown(f"**Channels:** {', '.join(angle.recommended_channels)}")
            st.markdown("**Headlines**")
            for headline in angle.headlines:
                st.markdown(f"- {headline}")
            st.markdown("**Body copy**")
            for body_copy in angle.body_copy:
                st.markdown(f"- {body_copy}")
            st.markdown("**CTAs**")
            for cta in angle.ctas:
                st.markdown(f"- {cta}")
            st.markdown("**Image prompts**")
            for prompt in angle.image_prompts:
                st.code(prompt, language="text")


def render_sidebar():
    st.sidebar.title("Operator Controls")
    st.sidebar.caption(
        "Use this dashboard as a quick demo of campaign data visibility and CRM handoff."
    )

    crm_provider = st.sidebar.selectbox("CRM Provider", ["Salesforce", "HubSpot"])
    dry_run = st.sidebar.checkbox("Dry run only", value=True)

    if os.getenv("STREAMLIT_DEBUG", "").lower() in {"1", "true", "yes"}:
        st.sidebar.write("Python executable:", sys.executable)
        st.sidebar.write("Python path:", sys.path)

    return crm_provider, dry_run


def render_hero(dataframe: pd.DataFrame | None):
    row_count = int(len(dataframe)) if dataframe is not None else 0
    has_income = dataframe is not None and "Income" in dataframe
    has_recency = dataframe is not None and "Recency" in dataframe
    avg_income = float(dataframe["Income"].mean()) if has_income else 0.0
    avg_recency = float(dataframe["Recency"].mean()) if has_recency else 0.0

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-kicker">CampaignForge AI</div>
            <div class="hero-title">Campaign Intelligence Dashboard</div>
            <div class="hero-copy">
                A lightweight operations view for reviewing campaign and customer segments,
                surfacing lead-scoring inputs, and demonstrating downstream CRM sync
                workflows from one interface.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Customer Rows", f"{row_count:,}")
    col2.metric("Average Income", f"{avg_income:,.0f}")
    col3.metric("Average Recency", f"{avg_recency:.1f}")


def render_dataset_panel(dataframe: pd.DataFrame | None, load_error: Exception | None):
    st.markdown('<div class="section-label">Dataset Preview</div>', unsafe_allow_html=True)
    if load_error is not None:
        st.error(f"Failed to load customer data: {load_error}")
        return

    if dataframe is None or dataframe.empty:
        st.warning("No customer data is currently available.")
        return

    preview_col, notes_col = st.columns([1.6, 1])
    with preview_col:
        st.dataframe(dataframe.head(25), use_container_width=True)
    with notes_col:
        st.markdown(
            """
            <div class="info-card">
                <strong>What this demonstrates</strong><br><br>
                Cleaned customer records flowing into a buyer-friendly dashboard layer that can
                support reporting, campaign analytics demos, and lightweight operational actions.
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_crm_panel(dataframe: pd.DataFrame | None, crm_provider: str, dry_run: bool):
    st.markdown("---")
    st.markdown('<div class="section-label">CRM Sync Demo</div>', unsafe_allow_html=True)
    st.subheader("Push a sample customer batch to Salesforce or HubSpot")
    st.caption(
        "Use dry-run mode for demos so you can show the integration flow without "
        "sending live records."
    )

    if st.button("Push 20 customers to CRM", type="primary"):
        if dataframe is None or dataframe.empty:
            st.error("No customer data available to push.")
            return

        records = build_crm_records(dataframe)
        try:
            if crm_provider == "Salesforce":
                client = SalesforceClient()
                result = client.push_leads(records, dry_run=dry_run)
            else:
                client = HubSpotClient()
                result = client.push_contacts(records, dry_run=dry_run)

            if result.get("dry_run"):
                st.info(
                    f"Dry run complete: prepared {result.get('sent', 0)} records "
                    f"for {crm_provider}. Endpoint: {result.get('endpoint')}"
                )
            else:
                st.success(
                    f"Sent {result.get('sent', 0)} records to {crm_provider} "
                    f"(status {result.get('status_code')})."
                )
        except Exception as exc:
            st.error(f"CRM push failed: {exc}")


def render_genai_panel():
    st.markdown("---")
    st.markdown('<div class="section-label">Brief Copilot</div>', unsafe_allow_html=True)
    st.subheader("Generate campaign angles, copy variants, and image prompts from a brief")
    st.caption(
        "This feature runs in mock mode by default for local demos. Set provider "
        "environment variables later for live LLM usage."
    )

    with st.form("genai-brief-form"):
        campaign_name = st.text_input("Campaign name", value="CampaignForge Product Launch")
        product_name = st.text_input("Product name", value="CampaignForge AI")
        target_market = st.text_input(
            "Target market",
            value="Agencies, freelancers, and startup marketing teams",
        )
        brief = st.text_area(
            "Campaign brief",
            value=(
                "Launch CampaignForge AI to teams that want a faster way to turn "
                "campaign ideas into structured messaging, reviewable outputs, and "
                "reusable campaign assets."
            ),
            height=160,
        )
        channels = st.multiselect(
            "Channels",
            ["LinkedIn", "Instagram", "Meta Ads", "Email", "Landing Page"],
            default=["LinkedIn", "Email", "Landing Page"],
        )
        tones = st.multiselect(
            "Tone options",
            ["Confident", "Practical", "Supportive", "Forward-Looking", "Direct"],
            default=["Confident", "Practical", "Forward-Looking"],
        )
        brand_keywords = st.text_input(
            "Brand keywords",
            value="modern, clean, structured, commercial",
        )
        submitted = st.form_submit_button("Generate campaign brief outputs", type="primary")

    if not submitted:
        return

    brief_model = CampaignBrief(
        campaign_name=campaign_name,
        product_name=product_name,
        target_market=target_market,
        brief=brief,
        goals=["generate qualified interest", "show a polished end-to-end workflow"],
        channels=channels,
        tones=tones,
        brand_keywords=[
            keyword.strip() for keyword in brand_keywords.split(",") if keyword.strip()
        ],
        compliance_notes=[
            "avoid hard performance promises and misleading before-and-after language"
        ],
    )
    principal = current_dashboard_principal()
    manifest = campaign_brief_service.generate_and_save(
        brief_model,
        workspace_id=principal.workspace_id,
        actor_user_id=principal.user_id,
    )
    st.success(f"Generated campaign output: {manifest.campaign_id} ({manifest.mode})")

    display_campaign_details(manifest)

    st.caption(
        "Saved manifest to "
        f"{manifest.artifacts.manifest_path} and copy output to "
        f"{manifest.artifacts.copy_output_path}."
    )


def render_campaign_history_panel() -> Optional[object]:
    st.markdown("---")
    st.markdown('<div class="section-label">Campaign History</div>', unsafe_allow_html=True)
    st.subheader("Reload, regenerate, and export saved campaigns")
    principal = current_dashboard_principal()
    campaigns = campaign_brief_service.list_campaigns(workspace_id=principal.workspace_id)
    if not campaigns:
        st.info("No saved campaigns yet.")
        return None

    campaign_options = {
        campaign_history_label(campaign): campaign for campaign in campaigns
    }
    selected_label = st.selectbox("Saved campaign history", list(campaign_options.keys()))
    selected_campaign = campaign_options[selected_label]
    st.caption(f"Created: {selected_campaign.created_at}")
    if selected_campaign.updated_at:
        st.caption(f"Last updated: {selected_campaign.updated_at}")

    action_col1, action_col2, action_col3 = st.columns(3)
    with action_col1:
        if st.button("Regenerate copy", key=f"regen-copy-{selected_campaign.campaign_id}"):
            selected_campaign = campaign_brief_service.regenerate(
                selected_campaign.campaign_id,
                CampaignRegenerationRequest(scope="copy"),
                workspace_id=principal.workspace_id,
            )
            st.success("Campaign copy regenerated.")
    with action_col2:
        if st.button("Regenerate prompts", key=f"regen-prompts-{selected_campaign.campaign_id}"):
            selected_campaign = campaign_brief_service.regenerate(
                selected_campaign.campaign_id,
                CampaignRegenerationRequest(scope="prompts"),
                workspace_id=principal.workspace_id,
            )
            st.success("Campaign prompts regenerated.")
    with action_col3:
        if st.button("Build export ZIP", key=f"build-export-{selected_campaign.campaign_id}"):
            export_path = campaign_export_service.export_campaign(
                selected_campaign.campaign_id,
                workspace_id=principal.workspace_id,
            )
            st.session_state[f"export-path-{selected_campaign.campaign_id}"] = str(export_path)
            st.success(f"Built export bundle: {export_path.name}")

    export_path_value = st.session_state.get(f"export-path-{selected_campaign.campaign_id}")
    if export_path_value:
        export_path = Path(export_path_value)
        if export_path.exists():
            with open(export_path, "rb") as handle:
                st.download_button(
                    "Download campaign ZIP",
                    data=handle.read(),
                    file_name=export_path.name,
                    mime="application/zip",
                    key=f"export-{selected_campaign.campaign_id}",
                )

    display_campaign_details(selected_campaign)
    return selected_campaign


def render_image_generation_panel():
    st.markdown("---")
    st.markdown('<div class="section-label">Image Concepts</div>', unsafe_allow_html=True)
    st.subheader("Generate concept images from saved campaign prompts")
    principal = current_dashboard_principal()
    campaigns = campaign_brief_service.list_campaigns(workspace_id=principal.workspace_id)
    if not campaigns:
        st.info("Generate a campaign brief first so image prompts are available.")
        return

    campaign_options = {
        campaign_history_label(campaign): campaign for campaign in campaigns
    }
    selected_campaign_label = st.selectbox("Saved campaign", list(campaign_options.keys()))
    selected_campaign = campaign_options[selected_campaign_label]

    angle_options = {
        angle_option_label(angle): angle
        for angle in selected_campaign.output.angles
    }
    selected_angle_label = st.selectbox("Campaign angle", list(angle_options.keys()))
    selected_angle = angle_options[selected_angle_label]
    prompt_options = selected_angle.image_prompts or ["No image prompts available"]
    selected_prompt = st.selectbox("Image prompt", prompt_options)
    style = st.text_input("Style direction", value="Campaign concept board")
    count = st.slider("Number of concepts", min_value=1, max_value=4, value=2)

    col1, col2 = st.columns([1, 1.6])
    with col1:
        if st.button("Generate concept images", type="primary"):
            manifest = campaign_image_service.generate_and_save(
                ImageGenerationRequest(
                    campaign_id=selected_campaign.campaign_id,
                    angle_id=selected_angle.angle_id,
                    prompt=selected_prompt,
                    style=style,
                    count=count,
                ),
                workspace_id=principal.workspace_id,
            )
            st.session_state["latest_image_manifest_id"] = manifest.campaign_id
            st.success(
                f"Saved {len(manifest.assets)} image concepts for "
                f"{manifest.campaign_id} ({manifest.mode})."
            )

    latest_manifest = campaign_image_service.load_manifest(
        selected_campaign.campaign_id,
        workspace_id=principal.workspace_id,
    )
    with col2:
        st.caption(
            "Mock SVG concepts are used locally by default. Set image provider "
            "environment variables later for live generation."
        )
        st.caption(f"Selected angle: {selected_angle.title}")

    if latest_manifest is None:
        st.info("No saved image concepts yet for this campaign.")
        return

    st.markdown("**Saved image set**")
    st.write(f"Style: {latest_manifest.style}")
    st.write(f"Prompt: {latest_manifest.prompt}")

    image_columns = st.columns(2)
    for index, asset in enumerate(latest_manifest.assets):
        image_path = campaign_storage.resolve_managed_path(asset.file_path)
        with image_columns[index % 2]:
            if image_path.exists():
                st.image(
                    str(image_path),
                    caption=f"{asset.style} ({asset.mode})",
                    use_container_width=True,
                )
            else:
                st.warning(f"Missing asset: {asset.file_path}")
            st.code(asset.prompt, language="text")
            st.caption(f"Status: {asset.approval_status}")
            approval_cols = st.columns(3)
            with approval_cols[0]:
                if st.button("Approve", key=f"approve-{asset.image_id}"):
                    latest_manifest = campaign_image_service.review_asset(
                        selected_campaign.campaign_id,
                        ImageReviewRequest(image_id=asset.image_id, approval_status="approved"),
                        workspace_id=principal.workspace_id,
                    )
                    st.rerun()
            with approval_cols[1]:
                if st.button("Reject", key=f"reject-{asset.image_id}"):
                    latest_manifest = campaign_image_service.review_asset(
                        selected_campaign.campaign_id,
                        ImageReviewRequest(image_id=asset.image_id, approval_status="rejected"),
                        workspace_id=principal.workspace_id,
                    )
                    st.rerun()
            with approval_cols[2]:
                if st.button("Reset", key=f"reset-{asset.image_id}"):
                    latest_manifest = campaign_image_service.review_asset(
                        selected_campaign.campaign_id,
                        ImageReviewRequest(image_id=asset.image_id, approval_status="pending"),
                        workspace_id=principal.workspace_id,
                    )
                    st.rerun()


def main():
    require_dashboard_access()
    render_styles()
    crm_provider, dry_run = render_sidebar()
    dataframe, load_error = load_customer_data()
    render_hero(dataframe)
    render_dataset_panel(dataframe, load_error)
    render_genai_panel()
    render_campaign_history_panel()
    render_image_generation_panel()
    render_crm_panel(dataframe, crm_provider, dry_run)


main()
