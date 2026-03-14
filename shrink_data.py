import xarray as xr

print("Opening dataset...")
ds = xr.open_dataset('dataset1.nc')

# Downsample: take every 2nd point to reduce size
ds_small = ds.isel(latitude=slice(0, None, 3), longitude=slice(0, None, 3))

# Save with high compression
encoding = {var: {'zlib': True, 'complevel': 7} for var in ds_small.data_vars}
print("Compressing... this might take a minute.")
ds_small.to_netcdf('dataset_final.nc', encoding=encoding)

print("Done! Check the size of 'dataset_final.nc'.")