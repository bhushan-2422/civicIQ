/* ============================================================
   Google Maps Helper — CivicIQ
   Manages map initialization for citizen complaint submission.
   ============================================================ */

const MapsHelper = (() => {
  let map = null;
  let marker = null;
  let isLoaded = false;

  /**
   * Initialize Google Maps on a given container element.
   * @param {string} containerId - DOM element ID for the map container.
   * @param {function} onLocationSelect - Callback with {lat, lng} when user picks a point.
   * @param {object} defaultCenter - Default map center {lat, lng}.
   */
  function initMap(containerId, onLocationSelect, defaultCenter = { lat: 18.5204, lng: 73.8567 }) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const apiKey = window.CIVIC_CONFIG && window.CIVIC_CONFIG.GOOGLE_MAPS_API_KEY;
    if (!apiKey) {
      console.warn('GOOGLE_MAPS_API_KEY not set. Map unavailable.');
      return;
    }

    // Load Google Maps API dynamically
    if (!window.google || !window.google.maps) {
      _loadScript(apiKey, () => _createMap(containerId, onLocationSelect, defaultCenter));
    } else {
      _createMap(containerId, onLocationSelect, defaultCenter);
    }
  }

  function _loadScript(apiKey, callback) {
    if (document.getElementById('gmaps-script')) {
      callback();
      return;
    }
    const script = document.createElement('script');
    script.id = 'gmaps-script';
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places,visualization`;
    script.async = true;
    script.defer = true;
    script.onload = () => {
      isLoaded = true;
      callback();
    };
    script.onerror = () => console.error('Failed to load Google Maps API');
    document.head.appendChild(script);
  }

  function _createMap(containerId, onLocationSelect, defaultCenter) {
    // Hide placeholder
    const placeholder = document.getElementById('map-placeholder');
    if (placeholder) placeholder.style.display = 'none';

    map = new google.maps.Map(document.getElementById(containerId), {
      center: defaultCenter,
      zoom: 13,
      mapTypeControl: false,
      fullscreenControl: false,
      streetViewControl: false,
      styles: _mapStyles(),
    });

    map.addListener('click', (event) => {
      const lat = event.latLng.lat();
      const lng = event.latLng.lng();
      _placeMarker({ lat, lng });
      if (onLocationSelect) onLocationSelect({ lat, lng });
    });
  }

  function _placeMarker(position) {
    if (marker) {
      marker.setPosition(position);
    } else {
      marker = new google.maps.Marker({
        position,
        map,
        title: 'Complaint Location',
        animation: google.maps.Animation.DROP,
        icon: {
          url: 'data:image/svg+xml,' + encodeURIComponent(`
            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="40" viewBox="0 0 32 40">
              <ellipse cx="16" cy="36" rx="8" ry="4" fill="rgba(0,0,0,0.2)"/>
              <path d="M16 0C7.164 0 0 7.164 0 16c0 10 16 24 16 24S32 26 32 16C32 7.164 24.836 0 16 0z" fill="#e8792b"/>
              <circle cx="16" cy="16" r="7" fill="white"/>
              <text x="16" y="20" text-anchor="middle" font-size="10" fill="#e8792b">📍</text>
            </svg>`),
          scaledSize: new google.maps.Size(32, 40),
          anchor: new google.maps.Point(16, 40),
        },
      });
    }
  }

  function setCenter(lat, lng, zoom = 15) {
    if (!map) return;
    const pos = { lat, lng };
    map.setCenter(pos);
    map.setZoom(zoom);
    _placeMarker(pos);
  }

  /**
   * Initialize a hotspot / heatmap for the officer dashboard.
   * @param {string} containerId
   * @param {Array} points - [{lat, lng, weight}]
   */
  function initHeatmap(containerId, points = []) {
    const apiKey = window.CIVIC_CONFIG && window.CIVIC_CONFIG.GOOGLE_MAPS_API_KEY;
    if (!apiKey) return;

    _loadScript(apiKey, () => {
      const heatmapData = points.map(p => ({
        location: new google.maps.LatLng(p.lat, p.lng),
        weight: p.weight || 1,
      }));

      const center = points.length > 0
        ? { lat: points[0].lat, lng: points[0].lng }
        : { lat: 18.5204, lng: 73.8567 };

      const heatMap = new google.maps.Map(document.getElementById(containerId), {
        center,
        zoom: 12,
        mapTypeControl: false,
        styles: _mapStyles(),
      });

      new google.maps.visualization.HeatmapLayer({
        data: heatmapData,
        map: heatMap,
        radius: 40,
      });

      // Add markers for high-priority complaints
      points.filter(p => p.priority >= 70).forEach(p => {
        new google.maps.Marker({
          position: { lat: p.lat, lng: p.lng },
          map: heatMap,
          title: `${p.category || 'Complaint'} - Priority ${p.priority}`,
          icon: {
            path: google.maps.SymbolPath.CIRCLE,
            scale: 8,
            fillColor: '#dc2626',
            fillOpacity: 0.9,
            strokeColor: '#fff',
            strokeWeight: 2,
          },
        });
      });
    });
  }

  /**
   * Initialize a markers-only map for dashboard hotspot view.
   * @param {string} containerId
   * @param {Array} points
   */
  function initMarkersMap(containerId, points = []) {
    const apiKey = window.CIVIC_CONFIG && window.CIVIC_CONFIG.GOOGLE_MAPS_API_KEY;
    if (!apiKey) return;

    _loadScript(apiKey, () => {
      const center = points.length > 0
        ? { lat: points[0].lat, lng: points[0].lng }
        : { lat: 18.5204, lng: 73.8567 };

      const markerMap = new google.maps.Map(document.getElementById(containerId), {
        center,
        zoom: 12,
        mapTypeControl: false,
        styles: _mapStyles(),
      });

      points.forEach(p => {
        const color = p.priority >= 70 ? '#dc2626' : p.priority >= 40 ? '#d97706' : '#16a34a';
        const m = new google.maps.Marker({
          position: { lat: p.lat, lng: p.lng },
          map: markerMap,
          title: `${p.category || 'Complaint'} — Priority ${(p.priority || 0).toFixed(1)}`,
          icon: {
            path: google.maps.SymbolPath.CIRCLE,
            scale: 10,
            fillColor: color,
            fillOpacity: 0.85,
            strokeColor: '#fff',
            strokeWeight: 2,
          },
        });

        const infoWindow = new google.maps.InfoWindow({
          content: `
            <div style="font-family:Inter,sans-serif;font-size:13px;padding:4px">
              <strong>${p.category || 'Unknown'}</strong><br>
              Priority: ${(p.priority || 0).toFixed(1)}/100<br>
              Status: ${p.status || 'N/A'}
            </div>`,
        });

        m.addListener('click', () => infoWindow.open(markerMap, m));
      });
    });
  }

  function _mapStyles() {
    return [
      { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#a0cbe8' }] },
      { featureType: 'road', elementType: 'geometry.stroke', stylers: [{ color: '#ffffff' }] },
      { featureType: 'poi', stylers: [{ visibility: 'simplified' }] },
    ];
  }

  return { initMap, setCenter, initHeatmap, initMarkersMap };
})();
