tailwind.config = {
    darkMode: "class",
    theme: {
        extend: {
            "gridTemplateColumns": {
                "16": "repeat(16, minmax(0, 1fr))"
            },
            "colors": {
                "surface-tint": "#adc6ff",
                "on-primary-fixed-variant": "#004395",
                "outline": "#8c909f",
                "tertiary-fixed": "#ffdcc6",
                "on-secondary": "#003824",
                "tertiary": "#ffb786",
                "surface-container-high": "#232a3a",
                "primary-fixed-dim": "#adc6ff",
                "primary-container": "#4d8eff",
                "surface-container": "#191f2f",
                "surface": "#0c1322",
                "inverse-primary": "#005ac2",
                "tertiary-container": "#df7412",
                "on-secondary-container": "#00311f",
                "on-tertiary": "#502400",
                "secondary-fixed-dim": "#4edea3",
                "surface-container-lowest": "#070e1d",
                "primary": "#adc6ff",
                "on-error-container": "#ffdad6",
                "secondary": "#4edea3",
                "error": "rgb(215 35 13)",
                "tertiary-fixed-dim": "#ffb786",
                "on-primary": "#002e6a",
                "outline-variant": "#424754",
                "on-error": "#690005",
                "background": "#0c1322",
                "secondary-fixed": "#6ffbbe",
                "secondary-container": "#00a572",
                "surface-bright": "#323949",
                "inverse-on-surface": "#293040",
                "primary-fixed": "#d8e2ff",
                "inverse-surface": "#dce2f7",
                "on-background": "#dce2f7",
                "on-secondary-fixed-variant": "#005236",
                "surface-dim": "#0c1322",
                "surface-container-highest": "#2e3545",
                "on-primary-container": "#00285d",
                "surface-variant": "#2e3545",
                "on-tertiary-fixed-variant": "#723600",
                "on-tertiary-fixed": "#311400",
                "on-tertiary-container": "#461f00",
                "on-surface": "#dce2f7",
                "on-secondary-fixed": "#002113",
                "error-container": "#93000a",
                "surface-container-low": "#141b2b",
                "on-primary-fixed": "#001a42",
                "on-surface-variant": "#c2c6d6"
            },
            "borderRadius": {
                "DEFAULT": "0.25rem",
                "lg": "0.5rem",
                "xl": "0.75rem",
                "full": "9999px"
            },
            "spacing": {
                "unit": "4px",
                "lg": "24px",
                "xs": "4px",
                "xl": "40px",
                "sm": "8px",
                "gutter": "24px",
                "container-max": "1440px",
                "md": "16px"
            },
            "fontFamily": {
                "display-lg-mobile": ["Inter"],
                "label-mono": ["JetBrains Mono"],
                "caption": ["Inter"],
                "headline-md": ["Inter"],
                "body-base": ["Inter"],
                "display-lg": ["Inter"]
            },
            "fontSize": {
                "display-lg-mobile": ["28px", { "lineHeight": "36px", "letterSpacing": "-0.02em", "fontWeight": "700" }],
                "label-mono": ["12px", { "lineHeight": "18px", "letterSpacing": "0.05em", "fontWeight": "500" }],
                "caption": ["12px", { "lineHeight": "14px", "letterSpacing": "0.01em", "fontWeight": "500" }],
                "headline-md": ["18px", { "lineHeight": "28px", "letterSpacing": "-0.01em", "fontWeight": "600" }],
                "body-base": ["14px", { "lineHeight": "20px", "letterSpacing": "0em", "fontWeight": "400" }],
                "display-lg": ["40px", { "lineHeight": "48px", "letterSpacing": "-0.02em", "fontWeight": "700" }]
            }
        }
    }
};
