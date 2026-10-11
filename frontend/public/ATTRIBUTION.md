# Local geographic assets

earth.png: NASA Visible Earth, Blue Marble land/ocean/ice2048, public-domain
NASA imagery (not a NASA endorsement). Original asset:
https://eoimages.gsfc.nasa.gov/images/imagerecords/57000/57730/land_ocean_ice_2048.png
The older57752 URL was404; the actual57730 source was downloaded successfully.

maps/land.geojson: Natural Earth1:110m land, public-domain geographic data.
https://www.naturalearthdata.com/about/terms-of-use/
https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_land.geojson

Both are served locally. If the texture fails, the application renders a local
map-based Earth material; no external image service is required at runtime.
