# flake8: noqa: E501,W293
from typing import Dict

from laughtrack.domain.entities.email import EmailTemplate


class EmailTemplateRegistry:
    """Registry for managing email templates."""

    def __init__(self):
        self._templates: Dict[str, EmailTemplate] = {}
        self._register_default_templates()

    def _register_default_templates(self):
        """Register default email templates."""
        # Dashboard report template
        self.register_template(
            EmailTemplate(
                template_id="dashboard_report",
                subject_template="Scraper Dashboard Report - {timestamp}",
                html_template="{dashboard_html}",
                default_from_name="Laughtrack Scraper System",
            )
        )

        # Session summary template
        self.register_template(
            EmailTemplate(
                template_id="session_summary",
                subject_template="Scraping Session Complete - {shows_scraped} shows found ({success_rate:.1f}% success)",
                html_template="""
                <html>
                <head>
                    <style>
                        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                        .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                        .header {{ background: #007acc; color: white; padding: 20px; text-align: center; }}
                        .content {{ padding: 20px; }}
                        .metrics {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                        .success {{ background: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin: 10px 0; }}
                        .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 10px 0; }}
                        .error {{ background: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 10px 0; }}
                        .footer {{ background: #f8f9fa; padding: 15px; text-align: center; color: #666; font-size: 0.9em; }}
                        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }}
                        .metric-item {{ text-align: center; }}
                        .metric-value {{ font-size: 1.5em; font-weight: bold; color: #007acc; }}
                        .metric-label {{ font-size: 0.9em; color: #666; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1 style="margin: 0;">Scraping Session Complete</h1>
                            <p style="margin: 10px 0 0 0; opacity: 0.9;">{timestamp}</p>
                        </div>
                        
                        <div class="content">
                            <div class="metrics">
                                <h3 style="margin-top: 0; color: #007acc;">Session Metrics</h3>
                                <div class="grid">
                                    <div class="metric-item">
                                        <div class="metric-value">{shows_scraped}</div>
                                        <div class="metric-label">Shows Scraped</div>
                                    </div>
                                    <div class="metric-item">
                                        <div class="metric-value">{shows_saved}</div>
                                        <div class="metric-label">Shows Saved</div>
                                    </div>
                                    <div class="metric-item">
                                        <div class="metric-value">{clubs_processed}</div>
                                        <div class="metric-label">Clubs Processed</div>
                                    </div>
                                    <div class="metric-item">
                                        <div class="metric-value">{success_rate:.1f}%</div>
                                        <div class="metric-label">Success Rate</div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="metrics">
                                <h3 style="margin-top: 0; color: #007acc;">Performance Details</h3>
                                <p><strong>Duration:</strong> {duration_minutes:.1f} minutes</p>
                                <p><strong>Shows Inserted:</strong> {shows_inserted:,}</p>
                                <p><strong>Shows Updated:</strong> {shows_updated:,}</p>
                                <p><strong>Failed Saves:</strong> {failed_saves}</p>
                                <p><strong>Total Errors:</strong> {errors}</p>
                            </div>
                            
                            {{# Status section based on errors #}}
                            {{% if errors == 0 %}}
                            <div class="success">
                                <h4 style="margin-top: 0; color: #155724;">✅ Perfect Session!</h4>
                                <p style="margin-bottom: 0;">All clubs scraped successfully with no errors.</p>
                            </div>
                            {{% else %}}
                            <div class="warning">
                                <h4 style="margin-top: 0; color: #856404;">⚠️ Session Completed with {errors} Error(s)</h4>
                                <p style="margin-bottom: 0;">Some clubs encountered issues during scraping.</p>
                            </div>
                            {{% endif %}}
                        </div>
                        
                        <div class="footer">
                            <p>This is an automated report from the Laughtrack Scraper System.</p>
                            <p>Generated at {timestamp}</p>
                        </div>
                    </div>
                </body>
                </html>
            """,
                default_from_name="Laughtrack Scraper System",
            )
        )

        # Comprehensive dashboard template
        self.register_template(
            EmailTemplate(
                template_id="comprehensive_dashboard",
                subject_template="Scraper Dashboard Report - {total_sessions} Sessions Analysis",
                html_template="""
                <html>
                <head>
                    <style>
                        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                        .container {{ max-width: 800px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                        .header {{ background: #007acc; color: white; padding: 20px; text-align: center; }}
                        .content {{ padding: 20px; }}
                        .section {{ margin: 20px 0; padding: 20px; border-radius: 8px; }}
                        .summary {{ background: #f8f9fa; }}
                        .latest {{ background: #e8f5e8; }}
                        .success {{ background: #d4edda; }}
                        .error {{ background: #f8d7da; }}
                        .warning {{ background: #fff3cd; }}
                        .footer {{ background: #f8f9fa; padding: 15px; text-align: center; color: #666; font-size: 0.9em; }}
                        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }}
                        .metric-item {{ text-align: center; }}
                        .metric-value {{ font-size: 1.5em; font-weight: bold; color: #007acc; }}
                        .metric-label {{ font-size: 0.9em; color: #666; }}
                        table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
                        th, td {{ padding: 8px; border: 1px solid #ddd; text-align: left; }}
                        th {{ background: #f8f9fa; }}
                        .text-right {{ text-align: right; }}
                        .success-text {{ color: #28a745; }}
                        .error-text {{ color: #dc3545; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1 style="margin: 0;">Scraper Metrics Dashboard</h1>
                            <p style="margin: 10px 0 0 0; opacity: 0.9;">Comprehensive Report - {timestamp}</p>
                        </div>
                        
                        <div class="content">
                            {dashboard_content}
                        </div>
                        
                        <div class="footer">
                            <p>This is an automated dashboard report from the Laughtrack Scraper System.</p>
                            <p>Generated at {timestamp}</p>
                        </div>
                    </div>
                </body>
                </html>
            """,
                default_from_name="Laughtrack Scraper System",
            )
        )

    def register_template(self, template: EmailTemplate):
        """Register a new email template."""
        self._templates[template.template_id] = template

    def get_template(self, template_id: str) -> EmailTemplate:
        """Get a template by ID."""
        if template_id not in self._templates:
            raise KeyError(f"Template '{template_id}' not found")
        return self._templates[template_id]

    def has_template(self, template_id: str) -> bool:
        """Check if a template exists."""
        return template_id in self._templates

    def list_templates(self) -> list[str]:
        """List all available template IDs."""
        return list(self._templates.keys())
