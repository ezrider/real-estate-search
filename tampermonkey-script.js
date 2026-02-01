// ==UserScript==
// @name         Real Estate Tracker - Realtor.ca
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Push listing data to Real Estate Tracker API
// @author       You
// @match        https://www.realtor.ca/listing/*
// @match        https://www.realtor.ca/property-details/*
// @match        https://www.condodork.com/*
// @grant        GM_xmlhttpRequest
// @grant        GM_notification
// @connect      your-domain.com
// ==/UserScript==

(function() {
    'use strict';

    // Configuration - Update these values
    // For production: https://condosapi.mistyrainbow.cloud/api/v1/listings
    const CONFIG = {
        API_URL: 'https://condosapi.mistyrainbow.cloud/api/v1/listings',
        API_KEY: 'YOUR_API_KEY_HERE',  // Get this from /var/www/condosapi/api/.env on your server
        PLATFORM: 'Realtor.ca'  // or 'CondoDork'
    };

    // Helper: Extract text by selector
    function getText(selector, parent = document) {
        const el = parent.querySelector(selector);
        return el ? el.textContent.trim() : null;
    }

    // Helper: Extract number from text
    function extractNumber(text) {
        if (!text) return null;
        const match = text.replace(/,/g, '').match(/[\d.]+/);
        return match ? parseFloat(match[0]) : null;
    }

    // Extract listing data from Realtor.ca
    function extractRealtorCaData() {
        const data = {
            source_platform: 'Realtor.ca',
            source_url: window.location.href
        };

        // MLS Number - usually in URL or meta tags
        const mlsMatch = window.location.href.match(/(\d+)/);
        data.mls_number = getText('[data-testid="listing-details__listing-id"]') ||
                          mlsMatch?.[1] ||
                          null;

        // Price
        const priceText = getText('[data-testid="listing-details__price"]') ||
                         getText('.listing-price');
        data.price = extractNumber(priceText);

        // Address
        data.address = getText('[data-testid="listing-details__address"]') ||
                      getText('.listing-address');

        // Unit number (if in address)
        const unitMatch = data.address?.match(/Unit\s+(\S+)/i) ||
                         data.address?.match(/#(\S+)/) ||
                         data.address?.match(/-(\d+)$/);
        data.unit_number = unitMatch?.[1] || null;

        // Property details
        const detailsSection = document.querySelector('[data-testid="property-details"]') ||
                               document.querySelector('.property-details');

        if (detailsSection) {
            const bedText = getText('[data-testid="bedrooms"]') ||
                           getText('.bedrooms');
            data.bedrooms = extractNumber(bedText);

            const bathText = getText('[data-testid="bathrooms"]') ||
                            getText('.bathrooms');
            data.bathrooms = extractNumber(bathText);

            const sqftText = getText('[data-testid="sqft"]') ||
                            getText('.square-feet');
            data.square_feet = extractNumber(sqftText);

            const propertyType = getText('[data-testid="property-type"]') ||
                                getText('.property-type');
            data.property_type = propertyType;
        }

        // Description
        data.description = getText('[data-testid="listing-description"]') ||
                          getText('.listing-description');

        // Agent info
        data.listing_agent = getText('[data-testid="listing-agent"]') ||
                            getText('.agent-name');

        // Building name (often in address or title)
        const titleText = document.title;
        const buildingMatch = titleText.match(/at\s+([^,]+)/);
        data.building_name = buildingMatch?.[1] || null;

        // Photos
        const photoElements = document.querySelectorAll('img[src*="realtor.ca"], img[data-src]');
        data.photos = Array.from(photoElements)
            .map(img => img.src || img.dataset.src)
            .filter(url => url && url.includes('realtor.ca'))
            .slice(0, 20); // Limit to 20 photos

        // Listing date (if available)
        const dateText = getText('[data-testid="listing-date"]') ||
                        getText('.listing-date');
        if (dateText) {
            data.listing_date = new Date(dateText).toISOString().split('T')[0];
        }

        return data;
    }

    // Extract listing data from CondoDork
    function extractCondoDorkData() {
        const data = {
            source_platform: 'CondoDork',
            source_url: window.location.href
        };

        // Price
        const priceText = getText('.price') || getText('[class*="price"]');
        data.price = extractNumber(priceText);

        // Address and building
        const addressText = getText('.address') || getText('[class*="address"]');
        data.address = addressText;

        // Extract building name from address or page title
        const titleMatch = document.title.match(/(.+?)\s+\|/);
        data.building_name = titleMatch?.[1] || null;

        // MLS number (if shown)
        const mlsText = document.body.textContent.match(/MLS[#]?\s*:?\s*(R?\d+)/i);
        data.mls_number = mlsText?.[1] || null;

        // Details - look for common patterns
        const detailsText = document.body.textContent;

        const bedMatch = detailsText.match(/(\d+)\s*Bed/i);
        data.bedrooms = bedMatch ? parseInt(bedMatch[1]) : null;

        const bathMatch = detailsText.match(/(\d+(?:\.\d+)?)\s*Bath/i);
        data.bathrooms = bathMatch ? parseFloat(bathMatch[1]) : null;

        const sqftMatch = detailsText.match(/(\d+)\s*sq\.?\s*ft/i);
        data.square_feet = sqftMatch ? parseInt(sqftMatch[1]) : null;

        // Photos
        const photoElements = document.querySelectorAll('img[src*="condodork"]');
        data.photos = Array.from(photoElements)
            .map(img => img.src)
            .slice(0, 20);

        return data;
    }

    // Send data to API
    function sendToAPI(data) {
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: 'POST',
                url: CONFIG.API_URL,
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': CONFIG.API_KEY
                },
                data: JSON.stringify(data),
                onload: function(response) {
                    if (response.status >= 200 && response.status < 300) {
                        resolve(JSON.parse(response.responseText));
                    } else {
                        reject(new Error(`HTTP ${response.status}: ${response.responseText}`));
                    }
                },
                onerror: reject
            });
        });
    }

    // Create the "Track Listing" button
    function createTrackButton() {
        const button = document.createElement('button');
        button.id = 're-tracker-btn';
        button.textContent = '🏠 Track Listing';
        button.style.cssText = `
            position: fixed;
            top: 100px;
            right: 20px;
            z-index: 99999;
            background: #D51B5D;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 12px 20px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            transition: all 0.2s;
        `;

        button.addEventListener('mouseenter', () => {
            button.style.background = '#b0174d';
            button.style.transform = 'scale(1.05)';
        });

        button.addEventListener('mouseleave', () => {
            button.style.background = '#D51B5D';
            button.style.transform = 'scale(1)';
        });

        button.addEventListener('click', async () => {
            button.textContent = '⏳ Saving...';
            button.disabled = true;

            try {
                // Determine which site we're on
                let data;
                if (window.location.hostname.includes('realtor.ca')) {
                    data = extractRealtorCaData();
                } else if (window.location.hostname.includes('condodork.com')) {
                    data = extractCondoDorkData();
                } else {
                    throw new Error('Unknown site');
                }

                // Validate required fields
                if (!data.mls_number && !data.address) {
                    throw new Error('Could not extract listing data. MLS or address required.');
                }

                console.log('[Real Estate Tracker] Extracted data:', data);

                // Send to API
                const result = await sendToAPI(data);

                // Show success notification
                GM_notification({
                    title: '✅ Listing Tracked',
                    text: result.message || 'Listing saved successfully',
                    timeout: 3000
                });

                button.textContent = '✓ Tracked!';
                button.style.background = '#28a745';

                setTimeout(() => {
                    button.textContent = '🏠 Track Listing';
                    button.style.background = '#D51B5D';
                    button.disabled = false;
                }, 2000);

            } catch (error) {
                console.error('[Real Estate Tracker] Error:', error);

                GM_notification({
                    title: '❌ Error',
                    text: error.message,
                    timeout: 5000
                });

                button.textContent = '❌ Error';
                button.style.background = '#dc3545';

                setTimeout(() => {
                    button.textContent = '🏠 Track Listing';
                    button.style.background = '#D51B5D';
                    button.disabled = false;
                }, 2000);
            }
        });

        document.body.appendChild(button);
    }

    // Initialize
    function init() {
        console.log('[Real Estate Tracker] Script loaded on', window.location.hostname);

        // Wait for page to load
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', createTrackButton);
        } else {
            createTrackButton();
        }
    }

    init();
})();
