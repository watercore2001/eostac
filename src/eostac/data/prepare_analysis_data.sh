python water_clarity_analysis.py \
-i /mnt/disk/xials/hkh/grid_data/water_clarity \
-o1 /mnt/disk/xials/hkh/grid_data/water_clarity_change \
-o2 /mnt/disk/xials/hkh/api_data/water_clarity_change \
-o3 /mnt/disk/xials/hkh/grid_data/water_clarity_statistics \
-o4 /mnt/disk/xials/hkh/api_data/water_clarity_statistics

python water_distribution_analysis.py \
-i /mnt/disk/xials/hkh/grid_data/water_distribution \
-o1 /mnt/disk/xials/hkh/grid_data/water_distribution_change \
-o2 /mnt/disk/xials/hkh/grid_data/water_distribution_statistics \
-o3 /mnt/disk/xials/hkh/api_data/water_distribution
