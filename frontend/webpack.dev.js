require('dotenv')
  .config({
    path: '../backend/uclapi/.env'
  });

const os = require('os');
const path = require('path');
const UglifyJsPlugin = require('uglifyjs-webpack-plugin');
const BundleTracker = require('webpack-bundle-tracker');

var entryPointsPathPrefix = './src/pages';

const publicPath = process.env.AWS_S3_STATICS
  ? `https://${process.env.AWS_S3_BUCKET_NAME}.s3.amazonaws.com/${process.env.AWS_S3_BUCKET_PATH}`
  : '/static/'

module.exports = {
  mode: 'development',
  optimization: {
    minimizer: []  // This list is built below as per platform requirements
  },
  plugins: [
    new UglifyJsPlugin({
      sourceMap: true
    }),
    new BundleTracker({
      filename: '../backend/uclapi/static/webpack-stats.json'
    })
  ],
  module: {
    rules: [
      {
        test: /\.jsx$/,
        exclude: /node_modules/,
        use: {
          loader: "babel-loader"
        }
      },
      {
        test: /\.scss$/,
        use: [
          { loader: "style-loader" },
          { loader: "css-loader" },
          { loader: "sass-loader" }
        ]
      },
      {
        test: /\.(jpg|png|svg)$/,
        loader: 'url-loader'
      },
    ]
  },
  entry: {
    getStarted: entryPointsPathPrefix + '/getStarted.jsx',
    documentation: entryPointsPathPrefix + '/documentation.jsx',
    dashboard: entryPointsPathPrefix + '/dashboard.jsx',
    marketplace: entryPointsPathPrefix + '/marketplace.jsx',
    authorise: entryPointsPathPrefix + '/authorise.jsx',
  },
  output: {
    path: path.resolve(__dirname, '../backend/uclapi/static/'),
    publicPath,
    filename: '[name].js'
  }
};
if (os.platform == "linux" && os.release().indexOf("Microsoft") != -1) {
  module.exports.optimization.minimizer.push(
    new UglifyJsPlugin({
      cache: true,
      sourceMap: true
    })
  );
} else {
  module.exports.optimization.minimizer.push(
    new UglifyJsPlugin({
      cache: true,
      sourceMap: true,
      parallel: true
    })
  );
}