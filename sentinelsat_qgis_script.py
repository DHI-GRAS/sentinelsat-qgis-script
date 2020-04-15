from qgis.processing import alg
import os
import logging
from qgis.PyQt.QtWidgets import QProgressBar

@alg(
    name="downloadsentinel",
    label=alg.tr("Download Sentinel"),
    group="sentineldownload",
    group_label=alg.tr("Sentinel Download"),
)
@alg.input(type=str, name='USER', label='Username')
@alg.input(type=str, name='PASSWORD', label='Password')
@alg.input(type=str, name='START', label='Start date (YYYYMMDD)', default='NOW-1DAY', optional=True)
@alg.input(type=str, name='END', label='End date (YYYYMMDD)', default='NOW', optional=True)
@alg.input(
    type=alg.ENUM,
    name="SENTINEL",
    label="Sentinel satellite constellation",
    default=0,
    options=["any", '1', '2', '3']
)
@alg.input(
    type=alg.EXTENT,
    name="EXTENT",
    label="Area of interest extent (geographic coordinates)",
    optional=True
)
@alg.input(
    type=alg.FILE,
    name="GEOMETRY_SHP",
    label="Area of interest .shp file (geographic coordinates - WGS84)",
    extension='shp',
    optional=True
)
@alg.input(
    type=alg.FILE,
    name="GEOMETRY_GJ",
    label="Area of interest .geojson file",
    extension='geojson',
    optional=True
)
@alg.input(type=int, name='CLOUD', label='Maximum cloud cover in percent', minValue=0, maxValue=100, default=0, optional=True)
@alg.input(
    type=alg.ENUM,
    name="INSTRUMENT",
    label="Instrument",
    default=0,
    options=['any', 'MSI', 'SAR-CSAR', 'SLSTR', 'OLCI', 'SRAL']
)
@alg.input(
    type=alg.ENUM,
    name="PRODUCTTYPE",
    label="Product type",
    default=0,
    options=['any', 'SLC', 'GRD', 'OCN', 'RAW', 'S2MSI1C', 'S2MSI2Ap']
)
@alg.input(type=str, name='UUID', label='Select products by UUID (comma-separated)', optional=True)
@alg.input(
    type=str,
    name='NAME',
    label='Select products by filename (supports wildcards)',
    optional=True
)
@alg.input(
    type=str,
    name='QUERY',
    label='Extra search keywords. Example: \'producttype=GRD,polarisationmode=HH\'',
    optional=True
)
@alg.input(
    type=str,
    name='URL',
    label='DHuS URL',
    default='https://scihub.copernicus.eu/apihub/',
    optional=True
)
@alg.input(
    type=int,
    name='LIMIT',
    label='Maximum number of products',
    minValue=0,
    maxValue=100000,
    default=0,
    optional=True
)
@alg.input(
    type=bool,
    name='DOWNLOAD',
    label='Download all results of the query',
    default=False
)
@alg.input(
    type=bool, 
    name='FOOTPRINTS',
    label='Create geojson file search_footprints.geojson with footprints and metadata',
    default=False
)
@alg.input(type=alg.FILE_DEST, name="PATH", label="Set the path where the the files will be saved")
def downloadsentinel(instance, parameters, context, feedback, inputs):
    """ downloadsentinel """

    logger = logging.getLogger('sentinelsat')

    logger_set = False  # only set once #TODO global doesnt work

    # _PROGRESS = progress  # from magic qgis namespace
    _PROGRESS = QProgressBar()

    def _extent_from_shpfile(path):
        import ogr
        drv = ogr.GetDriverByName('ESRI Shapefile')
        ds = drv.Open(path)
        if ds is None:
            raise IOError('Reading {} failed.'.format(path))
        try:
            layer = ds.GetLayer()
            extent = layer.GetExtent()
            extent_str = str(extent)[1:-1].replace(' ', '')
        finally:
            ds.Destroy()
        return extent_str


    def _extent_to_wkt(extent_str):
        return (
            'POLYGON(({0} {2},{1} {2},{1} {3},{0} {3},{0} {2}))'
            .format(*extent_str.split(',')))


    if parameters['GEOMETRY_SHP']:
        EXTENT = _extent_from_shpfile(parameters['GEOMETRY_SHP'])


    kwargs = dict(
        start=parameters['START'] or None,
        end=parameters['END'] or None,
        area_wkt=_extent_to_wkt(parameters['EXTENT']) if parameters['EXTENT'] else None,
        geometry=parameters['GEOMETRY_GJ'] or None,
        user=parameters['USER'],
        password=parameters['PASSWORD'],
        url=parameters['URL'],
        uuid=parameters['UUID'] or None,
        name=parameters['NAME'] or None,
        sentinel=[None, '1', '2', '3'][parameters['SENTINEL']],
        instrument=[None, 'MSI', 'SAR-C SAR', 'SLSTR', 'OLCI', 'SRAL'][parameters['INSTRUMENT']],
        producttype=[None, 'SLC', 'GRD', 'OCN', 'RAW', 'S2MSI1C', 'S2MSI2Ap'][parameters['PRODUCTTYPE']],
        cloud=parameters['CLOUD'] or None,
        query=parameters['QUERY'] or None,
        limit=parameters['LIMIT'] or None,
        download=parameters['DOWNLOAD'],
        path=parameters['PATH'],
        footprints=parameters['FOOTPRINTS'])


    class ProgressHandler(logging.StreamHandler):

        def __init__(self, progress):
            super(self.__class__, self).__init__()
            self.progress = progress

        def emit(self, record):
            msg = self.format(record)
            try:
                self.feedback.pushConsoleInfo(msg)
            except RuntimeError:
                pass  # no logging


    # class ProgressBar(object): TODO update with new progressbar()

    #     def __init__(self, total, initial=0.0, *args, **kwargs):
    #         self.qgis_progress = _PROGRESS
    #         self.value = initial
    #         self.total = total
    #         self.qgis_progress.setPercentage(self._get_percent())

    #     def _get_percent(self):
    #         return float(self.value) / self.total * 100

    #     def update(self, increment):
    #         self.value += increment
    #         self.qgis_progress.setPercentage(self._get_percent())

    #     def close(self):
    #         pass
    class ProgressBar(object):
        def __init__(self, *args, **kwargs):
            pass
        def _get_percent(self):
            pass
        def update(self, increment):
            pass
        def close(self):
            pass

    def _set_logger_handler(qgis_progress, level='INFO'):
        # global logger_set
        # if logger_set:
        #     return
        logger.setLevel(level)
        h = ProgressHandler(qgis_progress)
        h.setLevel(level)
        fmt = logging.Formatter('%(message)s')
        h.setFormatter(fmt)
        logger.addHandler(h)
        logger_set = True


    def _load_to_canvas(path):
        if path is not None and os.path.isfile(path):
            from processing.tools import dataobjects
            dataobjects.load(path, os.path.basename(path))


    def cli(user, password, geometry, start, end, uuid, name, download, sentinel, producttype,
            instrument, cloud, footprints, path, query, url, limit,
            area_wkt,
            order_by=None):
        """Search for Sentinel products and, optionally, download all the results
        and/or create a geojson file with the search result footprints.
        Beyond your Copernicus Open Access Hub user and password, you must pass a geojson file
        containing the geometry of the area you want to search for or the UUIDs of the products. If you
        don't specify the start and end dates, it will search in the last 24 hours.
        """
        import geojson as gj
        from sentinelsat.sentinel import SentinelAPI, SentinelAPIError, geojson_to_wkt, read_geojson

        returns = {}  # information to return

        api = SentinelAPI(user, password, url)
        api._tqdm = ProgressBar

        search_kwargs = {}
        if sentinel and not (producttype or instrument):
            search_kwargs["platformname"] = "Sentinel-" + sentinel

        if instrument and not producttype:
            search_kwargs["instrumentshortname"] = instrument

        if producttype:
            search_kwargs["producttype"] = producttype

        if cloud:
            if sentinel not in ['2', '3']:
                logger.error('Cloud cover is only supported for Sentinel 2 and 3.')
                raise ValueError('Cloud cover is only supported for Sentinel 2 and 3.')
            search_kwargs["cloudcoverpercentage"] = (0, cloud)

        if query is not None:
            search_kwargs.update((x.split('=') for x in query.split(',')))

        if area_wkt is not None:  # Pass through area_wkt
            search_kwargs['area'] = area_wkt
        elif geometry is not None:
            search_kwargs['area'] = geojson_to_wkt(read_geojson(geometry))

        if uuid is not None:
            uuid_list = [x.strip() for x in uuid.split(',')]
            products = {}
            for productid in uuid_list:
                try:
                    products[productid] = api.get_product_odata(productid)
                except SentinelAPIError as e:
                    if 'Invalid key' in e.msg:
                        logger.error('No product with ID \'%s\' exists on server', productid)
        elif name is not None:
            search_kwargs["identifier"] = name
            products = api.query(order_by=order_by, limit=limit, **search_kwargs)
        else:
            start = start or "19000101"
            end = end or "NOW"
            products = api.query(date=(start, end),
                                order_by=order_by, limit=limit, **search_kwargs)

        if footprints is True:
            footprints_geojson = api.to_geojson(products)
            footprints_file = os.path.join(path, "search_footprints.geojson")
            with open(footprints_file, "w") as outfile:
                outfile.write(gj.dumps(footprints_geojson))
            returns['footprints_file'] = footprints_file

        if download is True:
            product_infos, failed_downloads = api.download_all(products, path)
            if len(failed_downloads) > 0:
                with open(os.path.join(path, "corrupt_scenes.txt"), "w") as outfile:
                    for failed_id in failed_downloads:
                        outfile.write("%s : %s\n" % (failed_id, products[failed_id]['title']))
        else:
            for product_id, props in products.items():
                if uuid is None:
                    logger.info('Product %s - %s', product_id, props['summary'])
                else:  # querying uuids has no summary key
                    logger.info('Product %s - %s - %s MB', product_id, props['title'],
                                round(int(props['size']) / (1024. * 1024.), 2))
            if uuid is None:
                logger.info('---')
                logger.info('%s scenes found with a total size of %.2f GB',
                            len(products), api.get_products_size(products))

        return returns


    _set_logger_handler(_PROGRESS)
    logger.debug(kwargs)
    returns = cli(**kwargs)
    _load_to_canvas(returns.get('footprints_file', None))
